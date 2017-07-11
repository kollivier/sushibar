from datetime import datetime, timedelta, timezone
import re
import uuid

from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView
import redis

from sushibar.ccserverlib.services import ccserver_get_topic_tree
from sushibar.runs.models import ContentChannel, ContentChannelRun, ChannelRunStage


REDIS = redis.StrictRedis(host=settings.MMVP_REDIS_HOST,
                          port=settings.MMVP_REDIS_PORT,
                          db=settings.MMVP_REDIS_DB,
                          charset="utf-8",
                          decode_responses=True)





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



# DASHABOARD ###################################################################

class DashboardView(TemplateView):

    template_name = "pages/home.html"
    view_saved = False

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return super(DashboardView, self).get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['channels'] = {
            'Active Channels': [],
            'Inactive Channels': []
        }
        # TODO(arvnd): This can very easily be optimized by
        # querying the runs table directly.
        queryset = self.request.user.saved_channels if self.view_saved else ContentChannel.objects
        for channel in queryset.all():
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

            failed = any('fail' in x.name.lower() for x in last_run.events.all())

            # TODO(arvnd): check if channel is open.
            active = bool(last_run.chef_name)
            channel_list = context['channels']['Active Channels'] if active else context['channels']['Inactive Channels']

            channel_list.append({
                    "channel": channel.name,
                    "channel_url": "%s/%s/edit" % (channel.default_content_server, channel.channel_id),
                    "restart_color": 'success' if active else 'secondary',
                    "stop_color": "danger" if active else "secondary",
                    "id": channel.channel_id.hex,
                    "last_run": datetime.strftime(last_event.finished, "%b %d, %H:%M"),
                    "last_run_id": last_run.run_id,
                    "duration": str(timedelta(seconds=total_duration.seconds)),
                    "status": "Failed" if failed else last_event.name.replace("Status.",""),
                    "status_pct": get_status_pct(progress, failed),
                    "run_status": "danger" if failed else "success",
                    "chef_name": fmt_chef_name(last_run.chef_name),
                    "chef_link": make_chef_link(last_run.chef_name),
                    "cl_flags": fmt_cl_flags(last_run)
                })

        return context





# RUN DETAIL HELPERS ###########################################################

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'T', suffix)

# Darjeeling Limited
progress_bar_colors = ["#FF0000", "#00A08A", "#F2AD00", "#F98400", "#5BBCD6", "#ECCBAE", "#046C9A", "#D69C4E", "#ABDDDE", "#000000"]
resource_icons = {
    ".mp4": "fa-video-camera",
    ".png": "fa-file-image-o",
    ".pdf": "fa-file-pdf-o",
    ".zip": "fa-file-archive-o",
    "audio": "fa-volume-up",
    "topic": "fa-folder",
    "video": "fa-video-camera",
    "exercise": "fa-book",
    "document": "fa-file-text",
    "html5": "fa-file-code-o",
}

format_duration = lambda t: str(timedelta(seconds=t.seconds))

def get_run_stats(current_run_stats, previous_run_stats, format_value_fn = lambda x: x):
    if not current_run_stats:
        return []
    stats = []
    for k, v in current_run_stats.items():
        prev_value = previous_run_stats.get(k, 0) if previous_run_stats else 0
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
        context['total_time'] = format_duration(total_time)

        context['resource_counts'] = get_run_stats(run.resource_counts, previous_run.resource_counts if previous_run else None)
        context['resource_sizes'] = get_run_stats(run.resource_sizes, previous_run.resource_sizes if previous_run else None, sizeof_fmt)

        if self.request.user in run.channel.followers.all():
            # closed star if the user has already saved this.
            context['saved_icon_class'] = 'fa-star'
        else:
            context['saved_icon_class'] = 'fa-star-o'

        tree_data = ccserver_get_topic_tree(run)
        modify_data_recursively(tree_data)
        context['topic_tree'] = tree_data

        return context




# LOGS AND ERRORS ##############################################################

class RunErrorsView(TemplateView):

    def get_context_data(self, **kwargs):
        context = super(RunErrorsView, self).get_context_data(**kwargs)
        run_id = uuid.UUID(kwargs.get('runid', ''))
        run = ContentChannelRun.objects.get(run_id=run_id)
        # Depending on how big these are, it's probably bad to
        # load them in memory, we can use some file embed on S3, or
        # at minimum track a static folder and have the client side
        # load it.
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
        return context

