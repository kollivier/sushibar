from __future__ import absolute_import, unicode_literals

from celery.decorators import task
from celery.utils.log import get_task_logger
from django.core.management import call_command
from sushibar.runs.utils import load_tree_for_channel

logger = get_task_logger(__name__)



# runs the management command 'exportchannel' async through celery
@task(name='load_tree_for_channel_task')
def load_tree_for_channel_task(run_dict):
    """
    Fetches the detailed tree data from Kolibri Studio.
    Note: for large channels, this web request can take more than 30secs so we
    have turned this into a celery task to avoid blocking the request.
    """
    print('load_tree_for_channel_task received run_dict', run_dict)
    load_tree_for_channel(run_dict)
    # intentionally ignoring the return value (since json data is saved to disk)

