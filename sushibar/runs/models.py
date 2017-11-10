
from io import StringIO
import os
import uuid

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.db.models.signals import post_save
from django.utils.translation import ugettext as _

from sushibar.users.models import BarUser

__all__ = ["ContentChannel", "ContentChannelRun", "ChannelRunStage"]

class ContentChannel(models.Model):
    """
    The sushibar contect channel representation.
    """
    # id = local, implicit, autoincrementing integer primary key
    channel_id = models.UUIDField('The id from contentcuration.models.Channel')
    name = models.CharField(max_length=200, blank=True)  # equiv to ricecooker's `title`
    description = models.CharField(max_length=400, blank=True)
    version = models.IntegerField(default=0)
    source_domain = models.CharField(max_length=300, blank=True, null=True)
    source_id = models.CharField(max_length=200, blank=True, null=True)
    trello_url = models.TextField(blank=True, null=True)

    # Authorization-related fields for channel (not used in MMVP)
    registered_by_user = models.EmailField(max_length=200, blank=True, null=True)
    registered_by_user_token = models.CharField(max_length=200, blank=True, null=True)
    default_content_server = models.URLField(max_length=300, default=settings.DEFAULT_STUDIO_SERVER)

    # for temporal ordering
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    followers = models.ManyToManyField(BarUser, related_name="saved_channels")

    def get_last_run(self):
        try:
            return self.runs.latest("created_at")
        except ContentChannelRun.DoesNotExist:
            return None

    def get_status(self):
        try:
            last_run = self.get_last_run()
            return last_run and last_run.events.latest("finished").name
        except ChannelRunStage.DoesNotExist:
            return None

    def __str__(self):
        return '<Channel ' + self.channel_id.hex[:8] + '...>'

    class Meta:
        get_latest_by = "created_at"


def log_filename_for_run(run, filename):
    """Generate the log filename based on `channel_id` and `run_id`."""
    # Run logfile will be saved in MEDIA_ROOT/sushicheflogs/channel_id/run_id.log
    return 'sushicheflogs/{0}/{1}.log'.format(run.channel.channel_id.hex, run.run_id.hex)

def create_empty_logfile(sender, **kwargs):
    """Create an empty logfile for the ContentChannelRun after its inital save."""
    run_instance = kwargs["instance"]
    if kwargs["created"]:
        dummy_file = StringIO()
        run_instance.logfile.save('dummy_filename.log', dummy_file)

def update_run_state(sender, **kwargs):
    runstage_instance = kwargs["instance"]
    runstage_instance.run.state = runstage_instance.name
    runstage_instance.run.save()

class ContentChannelRun(models.Model):
    """
    A particular sushi chef run for the content channel `channel`.
    """
    run_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(ContentChannel, on_delete=models.CASCADE, related_name='runs')
    chef_name = models.CharField(max_length=200)
    ricecooker_version = models.CharField(max_length=100, blank=True, null=True)
    logfile = models.FileField(upload_to=log_filename_for_run, blank=True, null=True)

    # Channel stats
    resource_counts = JSONField(blank=True, null=True)
    resource_sizes = JSONField(blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)

    # Extra optional attributes like error counts, and command-line toggles (--staging / --publish / --update)
    extra_options = JSONField(blank=True, null=True)

    # Authorization fields
    started_by_user = models.EmailField(max_length=200, blank=True, null=True)
    started_by_user_token = models.CharField(max_length=200, blank=True, null=True)
    content_server = models.URLField(max_length=300, default=settings.DEFAULT_STUDIO_SERVER)

    # for temporal ordering
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '<Run ' + self.run_id.hex[:8] + '...>'

    def get_logs(self):
        context = {}
        logfile_path = self.logfile.path
        self.logfile.open(mode='r')
        context['logs'] = self.logfile.readlines()
        for level in 'critical', 'error':
            try:
                with open("%s.%s" % (logfile_path, level)) as f:
                    context[level] = f.readlines()
            except OSError:
                context[level] = []
                continue
        return context

    def get_tree_data_path(self):
        subfolder = "{}-{}".format(self.created_at.year, self.created_at.month)
        directory = os.path.sep.join([settings.TREES_DIR, self.channel.channel_id.hex, subfolder])
        if not os.path.exists(directory):
            os.makedirs(directory)

        write_to_path = os.path.join(directory, "{}.json".format(self.run_id.hex))
        return write_to_path


    class Meta:
        get_latest_by = "created_at"

post_save.connect(create_empty_logfile, sender=ContentChannelRun, dispatch_uid="logfilefix")



class ChannelRunStage(models.Model):
    """
    Represents different stages of the given channel run.
    """
    # id = local, implicit, autoincrementing integer primary key
    run = models.ForeignKey(ContentChannelRun, on_delete=models.CASCADE, related_name='events')
    name = models.CharField(max_length=100)
    started = models.DateTimeField(verbose_name=_("started"), blank=True, null=True)
    finished = models.DateTimeField(verbose_name=_("finished"), blank=True, null=True)
    duration = models.DurationField(verbose_name=_("duration"), blank=True, null=True)

    def get_duration_in_seconds(self):
       return self.duration.total_seconds()

    def __str__(self):
        return '<RunStage for run ' + self.run.run_id.hex[:8] + '...>'

post_save.connect(update_run_state, sender=ChannelRunStage, dispatch_uid="updatechannelrunstate")
