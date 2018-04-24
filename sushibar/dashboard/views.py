from collections import defaultdict
from datetime import datetime, timedelta, timezone
import json
import re
import uuid

from channels import Group
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.db.models import Q, Max
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.template.loader import render_to_string
from django.template import RequestContext
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.generic.base import TemplateView
import redis

from sushibar.ccserverlib.services import ccserver_get_topic_tree, get_channel_status_bulk, activate_channel, ccserver_publish_channel
from sushibar.runs.models import ContentChannel, ContentChannelRun, ChannelRunStage
from sushibar.services.trello.api import trello_add_card_to_channel

from .forms import ChannelCreateForm


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

def get_status_for_mapping(channel, mapping, run=None):
    return get_status(mapping.get(channel.channel_id.hex),  run=run)

def get_status(status, run=None, channel_id=None):
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
                    "url": run and "%s/channels/%s/staging" % (run.content_server, run.channel.channel_id.hex)
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
    return STATUS.get(status)


def get_bulk_status_mapping_for_channels_as_baruser(channels, baruser):
    """
    Makes "bulk requests" to Studio server to get channel status for all the
    channels we're about to display on the dashboard.
    Assumptions: baruser has access to 
    """
    status_mapping = {}
    # Group requests based on the Studio instance that we need to query
    channels_by_studio_server = defaultdict(list)
    for channel in channels:
        last_run = channels.exists() and channel.get_last_run()
        if last_run:
            studio_server = last_run.content_server
            if studio_server:
                channels_by_studio_server[studio_server].append(channel)
    #
    # Do batchs requests for statuses from all Kolibri servers
    for studio_server, channels in channels_by_studio_server.items():
        if 'learningequality.org' in studio_server:
            print('Making bulk request to', studio_server)
            channel_ids = [c.channel_id.hex for c in channels]
            statuses_dict = get_channel_status_bulk(studio_server, baruser.cctoken, channel_ids)
            status_mapping.update(statuses_dict)
        else:
            print('Skipping bulk request to', studio_server)
    #
    return status_mapping




# DASHABOARD ###################################################################
class DashboardView(LoginRequiredMixin, TemplateView):

    template_name = "pages/home.html"
    view_saved = False

    @method_decorator(ensure_csrf_cookie)
    def get(self, request, *args, **kwargs):
        return super(DashboardView, self).get(request, *args, **kwargs)

    def post(self, request):
        # create a form instance and populate it with data from the request:
        form = ChannelCreateForm(request.POST)
        # check whether it's valid:
        if form.is_valid():
            if ContentChannel.objects.filter(channel_id=form.cleaned_data['channel_id']).exists():
                form.add_error('domain', 'Channel with domain and source ID already exists')
                return HttpResponse(json.dumps({
                    'success': False,
                    'html': render_to_string("create_channel_modal.html", {'form': form}),
                }))

            channel = ContentChannel(
                spec_sheet_url=form.cleaned_data['spec_sheet_url'],
                chef_repo_url=form.cleaned_data['chef_repo'],
                channel_id=form.cleaned_data['channel_id'],
                name=form.cleaned_data['name'],
                source_domain=form.cleaned_data['domain'],
                source_id=form.cleaned_data['source_id'],
            )
            trello_add_card_to_channel(request, channel, form.cleaned_data['trello_url'])
            return HttpResponse(json.dumps({
                'success': True,
                'redirect_url': '/channels/{}/'.format(channel.channel_id.hex)
            }))
        return HttpResponse(json.dumps({
            'success': False,
            'html': render_to_string("create_channel_modal.html", {'form': form}),
        }))


    def get_context_data(self, **kwargs):
        context = super(DashboardView, self).get_context_data(**kwargs)
        context['form'] = ChannelCreateForm()
        context['channels'] = []

        channels = []
        if self.request.user.is_staff:
            channels = ContentChannel.objects.all()
        else:
            channel_ids = ContentChannelRun.objects\
                            .filter(Q(started_by_user_token=self.request.user.cctoken) | Q(channel__followers=self.request.user))\
                            .values_list('channel__id', flat=True).distinct()
            channels = ContentChannel.objects.filter(pk__in=channel_ids)

        channels = channels.annotate(last_run_date=Max('runs__modified_at')).order_by('-last_run_date')

        # Try to get channel status information from Kolibri Studio
        status_mapping = {}   # { "<channel_id>": "{{status_str}}", ... }
        try:
            status_mapping = get_bulk_status_mapping_for_channels_as_baruser(channels, self.request.user)
        except Exception as e:
            status_mapping = {}
            print('ERROR during get_bulk_status_mapping_for_channels_as_baruser, continuing...', e)

        # MAIN LOOP
        ########################################################################
        # TODO(arvnd): This can very easily be optimized by querying the runs table directly.
        for channel in channels:
            
            # Get the most recent run for the channel
            try:
                last_run = channel.runs.latest("created_at")
            except ContentChannelRun.DoesNotExist:
                print("No runs for channel %s " % channel.name, "continuing...")
                channel_data = {
                    "channel": channel.name,
                    "due_date": channel.due_date,
                    "id": channel.channel_id.hex,
                    "starred": self.request.user.is_authenticated and self.request.user.saved_channels.filter(channel_id=channel.channel_id).exists(),
                    "status": "New",
                    "spec_sheet_url": channel.spec_sheet_url,
                    "chef_repo_url": channel.chef_repo_url,
                }

                context['channels'].append(channel_data)

                continue

            try:
                last_event = last_run.events.latest("finished")
            except ChannelRunStage.DoesNotExist:
                print("No stages for run %s" % last_run.run_id.hex, "continuing...")
                continue

            progress = REDIS.hgetall(last_run.run_id.hex)
            total_duration = sum((event.duration for event in last_run.events.all()), timedelta())

            # Channels with errors are flagged in YELLLOW, channels with critical errors in RED
            logs = last_run.get_logs()
            failed = any(logs.get('critical'))
            warnings = any(logs.get('error'))

            # check if any daemonized chef is listening for control commands
            control_group = Group('control-' + channel.channel_id.hex)
            listeners = control_group.channel_layer.group_channels(control_group.name)
            active = True if len(listeners) > 0 else False

            starred = self.request.user.is_authenticated and self.request.user.saved_channels.filter(channel_id=channel.channel_id).exists()

            # Channel status according to Kolibri Studio (main soruce of truth)
            ccstatus = get_status_for_mapping(channel, status_mapping, run=last_run)

            channel_data = {
                "channel": channel.name,
                "due_date": channel.due_date,
                "trello_url": channel.trello_url,
                "run_needed": channel.run_needed,
                "changes_needed": channel.changes_needed,
                "channel_url": "%s/%s/edit" % (channel.default_content_server, channel.channel_id.hex),
                "restart_color": 'success' if active else 'secondary',
                "stop_color": "danger" if active else "secondary",
                "active": active,
                "id": channel.channel_id.hex,
                "ccstatus": ccstatus,
                "starred": starred,
                "last_run_date": datetime.strftime(last_event.finished, "%b %d, %H:%M"),
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
                "can_edit": self.request.user.is_staff or channel.runs.filter(started_by_user_token=self.request.user.cctoken).exists(),
            }
            context['channels'].append(channel_data)

        return context



# RUN DETAIL HELPERS ###########################################################

def sizeof_fmt(num, suffix='B'):
    if num:
        for unit in ['','K','M','G']:
            if abs(num) < 1024.0:
                return "%3.1f%s%s" % (num, unit, suffix)
            num /= 1024.0
        return "%.1f%s%s" % (num, 'T', suffix)
    else:
        return "0"

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

        # ROUTE = /channels/{{channel_id}}  ####################################
        if self.search_by_channel:
            channel_id = uuid.UUID(kwargs.get('channelid', ''))
            channel = ContentChannel.objects.get(channel_id=channel_id)

            if not channel.runs.exists():
                context['channel_status'] = "New"
                context['channel'] = channel
                context["can_edit"] = self.request.user.is_staff
                context['logged_in'] = not self.request.user.is_anonymous
                context['saved_icon_class'] = 'fa-star' if self.request.user in channel.followers.all() else 'fa-star-o'
                if channel.chef_repo_url:
                    context['pr_url'] = "{}/pulls".format(channel.chef_repo_url.rstrip('/'))
                context['request_storage_email'] = self.request.user.is_authenticated and self.request.user.email
                return context

            run = channel.runs.latest("created_at")

        # ROUTE = /runs/{{run_id}}  ############################################
        else:
            run_id = uuid.UUID(kwargs.get('runid', ''))
            run = ContentChannelRun.objects.get(run_id=run_id)

        # 2. get previous non-FAILURE run
        previous_run = None
        previous_runs = run.channel.runs.all().order_by('-created_at')[:1]
        for candiate_run in previous_runs:
            failed = any('FAILURE' in x.name for x in candiate_run.events.all())
            if not failed:
                previous_run = candiate_run
                break

        try:
            status_dict = get_channel_status_bulk(run.content_server, run.started_by_user_token, [run.channel.channel_id.hex])
            if status_dict:
                channel_status = status_dict[run.channel.channel_id.hex]
                context['channel_status'] = channel_status
                context['actions'] = get_status(channel_status, run=run)['actions']
        except Exception:
            pass

        context['channel'] = run.channel
        context['run'] = run

        run.extra_options = run.extra_options or {}
        context['channel_run_status'] = "staged" if run.extra_options.get("staged") else None
        context['channel_run_status'] = "published" if run.extra_options.get("published") else None
        context['channel_run_status'] = context['channel_run_status'] or context.get('channel_status') or "created"

        baruser = self.request.user
        context['logged_in'] = not baruser.is_anonymous
        if baruser.is_anonymous:
            context["can_edit"] = False
        else:
            baruser_has_runs = run.channel.runs.filter(started_by_user_token=baruser.cctoken).exists()
            context["can_edit"] = self.request.user.is_staff or baruser_has_runs

        context['channel_runs'] = run.channel.runs.all().order_by("-created_at")
        context['last_run_date'] = run.channel.get_last_run().modified_at

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

        if baruser in run.channel.followers.all():
            # closed star if the baruser has saved this channel
            context['saved_icon_class'] = 'fa-star'
        else:
            context['saved_icon_class'] = 'fa-star-o'

        tree_data = []
        try:
            with open(run.get_tree_data_path(), 'r') as tree_file:
                tree_data = json.load(tree_file)
        except FileNotFoundError:
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
        context['request_storage_email'] = run.started_by_user or self.request.user.is_authenticated and self.request.user.email

        return context
