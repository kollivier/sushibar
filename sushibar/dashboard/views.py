from datetime import datetime, timedelta, timezone
import json
import re
import uuid

from django.conf import settings
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import redirect
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView
import redis

from sushibar.ccserverlib.services import ccserver_get_topic_tree, get_channel_status_bulk, activate_channel, ccserver_publish_channel
from sushibar.runs.models import ContentChannel, ContentChannelRun, ChannelRunStage


REDIS = redis.StrictRedis(host=settings.MMVP_REDIS_HOST,
                          port=settings.MMVP_REDIS_PORT,
                          db=settings.MMVP_REDIS_DB,
                          charset="utf-8",
                          decode_responses=True)


def open_channel_page(request, channel):
    channel = ContentChannel.objects.get(channel_id=uuid.UUID(channel))
    last_run = channel.get_last_run()
    return redirect('runs', last_run and last_run.run_id)

def deploy_channel(request, channelid):
    status, response = activate_channel(request.user, channelid)
    if status == "failure":
        return HttpResponseBadRequest(response)
    return HttpResponse(response)

def publish_channel(request, channelid):
    status, response = ccserver_publish_channel(request.user, channelid)
    if status == "failure":
        return HttpResponseBadRequest(response)
    return HttpResponse(response)

# DASHABOARD HELPERS ###########################################################

def get_status_pct(progress, failed):
    fmt_pct = lambda f: int(float(f) * 100)
    if failed:
        return 100
    if progress is None:
        return 0
    return fmt_pct(progress.get('progress', 0))

def fmt_cl_flags(run):
    if not run.extra_options:
        return ""
    return " ".join("--%s=%s" % (k, v) for k, v in run.extra_options.items())

def make_chef_link(chef_name):
    return re.sub(r'git:[\w\d]+$', 'git', chef_name).replace("git+ssh://git@", "https://")

def fmt_chef_name(chef_name):
    return re.sub(r'git:[\w\d]+$', 'git', chef_name).replace("github.com","").replace("https://", "").replace("git+ssh://git@", "")


def get_status(channel, mapping, run=None):
    STATUS = {
        "deleted": {
            "name": "Deleted",
            "helper": "Channel has been deleted",
        },
        "staged": {
            "name": "Needs Review",
            "helper": "Channel is currently staged",
            "actions": [
                {
                    "action_text": "Review Channel",
                    "url": run and "%s/channels/%s/staging" % (run.content_server, channel.channel_id.hex)
                }
            ]
        },
        "unpublished": {
            "name": "Needs Publishing",
            "helper": "Channel has unpublished updates",
        },
        "active": {
            "name": "Active",
            "helper": "Channel is active",
        },
        "building" : {
            "name": "Building...",
            "helper": "Building topic tree for this channel",
        },
    }
    return STATUS.get(mapping.get(channel.channel_id.hex))

# DASHABOARD ###################################################################

class DashboardView(TemplateView):

    template_name = "pages/home.html"
    view_saved = False

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return super(DashboardView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['channels'] = []

        channels = ContentChannel.objects.all()
        status_mapping = {}

        try:
            status, channel_status = get_channel_status_bulk(self.request.user, [c.hex for c in channels.values_list('channel_id', flat=True)])
            if status == "success":
                status_mapping = channel_status['statuses']
        except Exception:
            pass

        # TODO(arvnd): This can very easily be optimized by
        # querying the runs table directly.
        for channel in channels:
            # TODO(arvnd): add active bit to channel model and
            # split on that.
            try:
                last_run = channel.runs.latest("created_at")
            except ContentChannelRun.DoesNotExist:
                print("No runs for channel %s " % channel.name)
                continue

            try:
                last_event = last_run.events.latest("finished")
            except ChannelRunStage.DoesNotExist:
                print("No stages for run %s" % last_run.run_id.hex)
                continue

            progress = REDIS.hgetall(last_run.run_id.hex)
            total_duration = sum((event.duration for event in last_run.events.all()), timedelta())

            logs = last_run.get_logs()

            failed = any(logs.get('critical'))
            warnings = any(logs.get('error'))

            # TODO(arvnd): check if channel is open.
            active = bool(last_run.chef_name)
            starred = self.request.user.is_authenticated and self.request.user.saved_channels.filter(channel_id=channel.channel_id).exists()

            channel_data = {
                "channel": channel.name,
                "channel_url": "%s/%s/edit" % (channel.default_content_server, channel.channel_id.hex),
                "restart_color": 'success' if active else 'secondary',
                "stop_color": "danger" if active else "secondary",
                "active": active,
                "id": channel.channel_id.hex,
                "ccstatus": get_status(channel, status_mapping, run=last_run),
                "starred": starred,
                "last_run": datetime.strftime(last_event.finished, "%b %d, %H:%M"),
                "last_run_id": last_run.run_id,
                "duration": str(timedelta(seconds=total_duration.seconds)),
                "status": "Failed" if failed else last_event.name.replace("Status.","").replace("_", " "),
                "status_pct": get_status_pct(progress, failed),
                "run_status": "danger" if failed else "success",
                "chef_name": fmt_chef_name(last_run.chef_name),
                "chef_link": make_chef_link(last_run.chef_name),
                "cl_flags": fmt_cl_flags(last_run),
                "failed_count": failed and len(logs.get('critical')),
                "warning_count": warnings and len(logs.get('error')),
            }

            context['channels'].append(channel_data)

        return context





# RUN DETAIL HELPERS ###########################################################

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'T', suffix)

# Darjeeling Limited
progress_bar_colors = ["#F3BE1A", "#66321C", "#FFA475", "#067586", "#C87533", "#52656B", "#CF5351", "#4F4B59", "#738F1E", "#037784"]

resource_icons = {
    ".mp4": "fa-video-camera",
    ".mp3": "fa-headphones",
    ".png": "fa-file-image-o",
    ".pdf": "fa-file-pdf-o",
    ".zip": "fa-file-archive-o",
    "audio": "fa-volume-up",
    "topic": "fa-folder",
    "video": "fa-video-camera",
    "exercise": "fa-book",
    "document": "fa-file-text",
    "html5": "fa-file-code-o",
    "total": "",
}

format_duration = lambda t: str(timedelta(seconds=t.seconds))

def get_run_stats(current_run_stats, previous_run_stats, format_value_fn = lambda x: x):
    if not current_run_stats:
        return []
    stats = []
    for k, v in current_run_stats.items():
        v = v or 0
        prev_value = previous_run_stats.get(k) or 0 if previous_run_stats else 0
        bg_class = "table-default"
        if v < prev_value:
            bg_class = "table-danger"
        elif v > prev_value:
            bg_class = "table-success"
        stats.append({
                "icon": resource_icons.get(k, "fa-file"),
                "name": k,
                "value": format_value_fn(v),
                "previous_value": format_value_fn(prev_value) if prev_value else "-",
                "bg_class": bg_class,
            })
    return stats

def modify_data_recursively(data):
    for root in data:
        root["icon"] = resource_icons.get(root["kind"], "fa-file")
        if "file_size" in root:
            root["file_size"] = sizeof_fmt(root["file_size"])
        if "children" in root:
            modify_data_recursively(root["children"])


# RUN DETAIL ###################################################################

class RunView(TemplateView):
    template_name = "pages/runs.html"
    search_by_channel = False

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return super(RunView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(RunView, self).get_context_data(**kwargs)
        run = None
        if self.search_by_channel:
            channel_id = uuid.UUID(kwargs.get('channelid', ''))
            channel = ContentChannel.objects.get(channel_id=channel_id)
            run = channel.runs.latest("created_at")
        else:
            run_id = uuid.UUID(kwargs.get('runid', ''))
            run = ContentChannelRun.objects.get(run_id=run_id)
        # TODO(arvnd): The previous run will be wrong for any run that
        # is not the most recent.
        previous_run = run.channel.runs.all()[:2]
        if len(previous_run) < 2:
            previous_run = None
        else:
            previous_run = previous_run[1]

        try:
            status, channel_status = get_channel_status_bulk(self.request.user, [run.channel.channel_id.hex])
            if status == 'success':
                context['actions'] = get_status(run.channel, channel_status['statuses'], run=run)['actions']

        except Exception:
            pass

        context['channel'] = run.channel
        context['run'] = run
        context['run_stages'] = []
        total_time = timedelta()
        for idx, stage in enumerate(run.events.order_by('finished').all()):
            context['run_stages'].append({
                "duration": stage.duration,
                "name": stage.name.replace("Status.",""),
                "color": progress_bar_colors[idx % len(progress_bar_colors)]})
            total_time += stage.duration
        for stage in context['run_stages']:
            stage['percentage'] = stage['duration'] / total_time * 100 if total_time.seconds > 0 else 0
            stage['duration'] = format_duration(stage['duration'])
            stage['readable_name'] = stage['name'].replace("_", " ")
        context['total_time'] = format_duration(total_time)

        context['resource_counts'] = get_run_stats(run.resource_counts, previous_run.resource_counts if previous_run else None)
        context['resource_sizes'] = get_run_stats(run.resource_sizes, previous_run.resource_sizes if previous_run else None, sizeof_fmt)

        context['combined_stats'] = []
        context['topic_count'] = {"value": "-", "previous_value": "-"}
        for count in context['resource_counts']:
            if count['name'] == 'topic':
                context['topic_count'] = count
            else:
                count['size'] = next(size for size in context['resource_sizes'] if size['name'] == count['name'])
                context['combined_stats'].append(count)

        if self.request.user in run.channel.followers.all():
            # closed star if the user has already saved this.
            context['saved_icon_class'] = 'fa-star'
        else:
            context['saved_icon_class'] = 'fa-star-o'

        tree_data = ccserver_get_topic_tree(run)
        modify_data_recursively(tree_data)
        context['topic_tree'] = tree_data

        logfile_path = run.logfile.path
        run.logfile.open(mode='r')
        context['logs'] = run.logfile.readlines()
        for level in 'critical', 'error':
            try:
                with open("%s.%s" % (logfile_path, level)) as f:
                    context[level] = f.readlines()
            except OSError:
                context[level] = []
                continue

        context['channel_url'] = "%s/%s/edit" % (run.channel.default_content_server, run.channel.channel_id.hex)

        return context
