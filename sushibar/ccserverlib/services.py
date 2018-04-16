import json

from django.conf import settings
import requests

BASE_URL = settings.DEFAULT_STUDIO_SERVER
# TODO(Ivan) need to think about this, because BASE_URL could be different on a
# per-channel basis, so might want to pass paths below as "templates" and let the
# calling function fill them in using `run.content_server`    @Jordan: thoughts?

PUBLISH_CHANNEL_URL = "%s/api/internal/publish_channel" % BASE_URL
GET_CHANNELS_URL = "%s/get_user_channels" % BASE_URL
CHECK_USER_URL = "%s/api/internal/check_user_is_editor" % BASE_URL
ACTIVATE_CHANNEL_URL = "%s/api/internal/activate_channel_internal" % BASE_URL
GET_CHANNEL_STATUS_URL = "%s/api/internal/get_channel_status" % BASE_URL
FINISH_CHANNEL_URL = "%s/api/internal/finish_channel" % BASE_URL

def post_request(baruser, auth_url, data=None):
    if not baruser.is_authenticated or not baruser.cctoken:
        return ('failure', 'User does not have a Kolibri Studio token')
    try:
        request = requests.post(
                auth_url,
                data=json.dumps(data),
                headers={'Authorization': 'Token %s' % baruser.cctoken,
                         'Content-Type': 'application/json'})
        if request.status_code == 200:
            return ('success', request.json())
        else:
            return ('failure', 'Request failed: %s' % request.reason)

    except requests.ConnectionError: # fallback when ccserver can't be reached
        return ('failure', 'Connection error: could not reach the ccserver.')

def get_request(baruser, auth_url, data=None):
    if not baruser.is_authenticated or not baruser.cctoken:
        return ('failure', 'User does not have a Kolibri Studio token')

    try:
        request = requests.get(
                auth_url,
                data=json.dumps(data or {}),
                headers={'Authorization': 'Token %s' % baruser.cctoken,
                         'Content-Type': 'application/json'})
        if request.status_code == 200:
            return ('success', request.json())
        else:
            return ('failure', 'Request failed: %s' % request.reason)

    except requests.ConnectionError: # fallback when ccserver can't be reached
        return ('failure', 'Connection error: could not reach the ccserver.')


def ccserver_authenticate_user(cctoken, ccemail=None):
    """
    Check if `cctoken` is recognized by Content Curation Server (CC Server).
    If `ccemail` is given, we'll also make sure `ccemail` matches the email of
    the account on the CC Server.

    Wrapper around `api/internal/authenticate_user_internal` which attempts to
    log user in based on token, throws 400 error if user token is invalid
        POST
        Header:
         { "Authorization": "Token {token}"}
        Body: ---
        Response:
        {
            "success" : True,
            "username" : "{username}"
        }

    Returns tuple `(status, email_or_msg)`, where `status` is one of:
      - `status='success'` if authenication with CC Server succeds and `email_or_msg` (str)
         will contain the email address associated with `cctoken` on the CC Server.
      - `status='failure'` if `cctoken` is not recognized as as a valid token
         for any CCUser in this case `email_or_msg` (str) is the reason for the failure.
    """
    ccserver_base_url = settings.DEFAULT_STUDIO_SERVER
    auth_url = "%s/api/internal/authenticate_user_internal" % ccserver_base_url
    try:
        request = requests.post(
                auth_url,
                data=json.dumps({}),
                headers={'Authorization': 'Token %s' % cctoken,
                         'Content-Type': 'application/json'})
        response_data = request.json()
        if request.ok and response_data['success']:
            if ccemail and ccemail != response_data['username']:
                return ('failure', 'Token valid but CC Server has a different email file.')

            print('Successfully authenticated against CCServer')
            return ('success', response_data)

        else: # e.g. Error 403 Unauthorized
            return ('failure', 'Failed to authenticate against CCServer (`cctoken` not recognized)')

    except requests.ConnectionError: # fallback when ccserver can't be reached
        return ('failure', 'Connection error: could not reach the ccserver.')



def ccserver_publish_channel(baruser, channel_id):
    """
        returns {"success": True, "channel_id": str}
    """
    return post_request(baruser, PUBLISH_CHANNEL_URL, data={"channel_id": channel_id})


def get_user_channels(baruser):
    """
        returns serialized channel list
    """
    return get_request(baruser, GET_CHANNELS_URL)


def check_user_is_editor(baruser, channel_id):
    """
        returns success if user is an editor
    """
    return post_request(baruser, CHECK_USER_URL, data={"channel_id": channel_id})



def finish_channel(baruser, channel_id, stage=False):
    """
        Moves chef tree to either staging tree or main tree depending on user specification
    """
    return post_request(baruser, FINISH_CHANNEL_URL, data={"channel_id": channel_id})


def activate_channel(baruser, channel_id):
    """
        activates staged channels
    """
    return post_request(baruser, ACTIVATE_CHANNEL_URL, data={"channel_id": channel_id})



def get_channel_status_bulk(content_server, cctoken, channel_ids):
    """
    Retrieve a dict of channel statuses in bulk from Kolibri Studio.
    Uses authorization Token `cctoken` to make the request.
    """
    no_data = {}
    try:
        response = requests.post(
                "%s/api/internal/get_channel_status_bulk" % content_server,
                data=json.dumps({"channel_ids": channel_ids}),
                headers={'Authorization': 'Token %s' % cctoken,
                         'Content-Type': 'application/json'})
        if response.ok:
            response_data = response.json()
            if response_data['success']:
                return response_data['statuses']
    except requests.ConnectionError:   # fallback when ccserver can't be reached
        print('ConnectionError, returning default empty dict {}')

    return no_data



def get_staged_diff(baruser, channel_id):
    pass
# api/internal/get_staged_diff_internal
# Returns a list of changes between the main tree and the staged tree
# (Includes date/time created, file size, # of each content kind, # of questions, and # of subtitles)
# POST
# Header: ---
# Body:
# {"channel_id": "{uuid.hex}"}
# List of json changes. Example:
# [
#     {
#         "field" : "File Size",
#         "live" :  100 (# bytes),
#         "staged" : 200 (# bytes),
#         "difference" : 100,
#         "format_size" : True
#     }
# ]


def compare_trees(baruser, channel_id, tree='staging'):
    """
    POST /api/internal/compare_trees
    Returns a dict of new nodes and deleted nodes between either:
     - the staging tree and the previous tree (when staging=true)
     - or main tree and the previous tree (when staging=false)
    """
    staging = True if tree == 'staging' else False
    try:
        request = requests.post(
                "%s/api/internal/compare_trees" % settings.DEFAULT_STUDIO_SERVER,
                data=json.dumps({
                    "channel_id": channel_id,
                    "staging": staging,
                }),
                headers={'Authorization': 'Token %s' % baruser.cctoken,
                         'Content-Type': 'application/json'})
        if request.ok:
            return request.json()
        else:
            print('ERROR', request.status)
    except requests.ConnectionError as e:   # fallback when ccserver can't be reached
        pass
    return {}

def ccserver_get_topic_tree(run):
    """
    This used to call the API endpoint `/api/internal/get_tree_data` but it was
    not reliable (request times out for large channels), so we're replacing it
    with a multiple calls to `/api/internal/get_node_tree_data` (defined below).
    """
    from sushibar.runs.utils import load_tree_for_channel
    run_dict = dict(
        content_server=run.content_server,
        channel_id=run.channel.channel_id.hex,
        started_by_user_token=run.started_by_user_token,
        tree_data_path=run.get_tree_data_path(),
    )
    tree_data = load_tree_for_channel(run_dict)
    return tree_data

def ccserver_get_node_children(run_dict, node_id=None):
    """
    Retrieve from Kolibri Studio json data for children of `node_id` for the run
    info provided in `run_dict`. If node_id is None, we retrieve the channel root.
    """
    data = []
    try:
        request = requests.post(
                "%s/api/internal/get_node_tree_data" % run_dict['content_server'],
                data=json.dumps({"node_id" : node_id, "channel_id": run_dict['channel_id']}),
                headers={'Authorization': 'Token %s' % run_dict['started_by_user_token'],
                         'Content-Type': 'application/json'})
        if request.ok:
            data = request.json().get("tree", [])
    except requests.ConnectionError:   # fallback when ccserver can't be reached
        pass
    return data

def ccserver_check_channel_staged(run):
    data = []
    try:
        request = requests.post(
                "%s/api/internal/check_channel_is_staged" % run.content_server,
                data=json.dumps({"channel_id": run.channel.channel_id.hex}),
                headers={'Authorization': 'Token %s' % run.started_by_user_token,
                         'Content-Type': 'application/json'})
        if request.ok:
            data = request.json().get("staged", False)
    except requests.ConnectionError:   # fallback when ccserver can't be reached
        pass
    return data
# api/internal/get_tree_data
# Returns a simplified dict of the specified tree
# POST
# Header: ---
# Body:
# {
#     "channel_id": "{uuid.hex}",
#     "tree": "{str}"
# }
# Tree can be "main", "chef", "staging", or "previous"
#
#
# {
#     "success" : True,
#     "tree" : [list of node dicts]
# }
#
# Example of tree:
# [
#     {
#         'kind': 'topic',
#         'title': 'Topic',
#         'children': [
#             {
#                 'kind': 'exercise',
#                 'title': 'Exercise'
#                 'count': 2
#             }
#         ]
#     },
#     {
#         'kind': 'html5',
#         'title': 'HTML Title',
#         'file_size': 145990
#     },
# ]
