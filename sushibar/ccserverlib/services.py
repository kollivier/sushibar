import json

from django.conf import settings
import requests

BASE_URL = "http://127.0.0.1:8000" # settings.DEFAULT_CONTENT_CURATION_SERVER

PUBLISH_CHANNEL_URL = "%s/api/internal/publish_channel" % BASE_URL
GET_CHANNELS_URL = "%s/get_user_channels" % BASE_URL
CHECK_USER_URL = "%s/api/internal/check_user_is_editor" % BASE_URL
ACTIVATE_CHANNEL_URL = "%s/api/internal/activate_channel_internal" % BASE_URL
GET_CHANNEL_STATUS_URL = "%s/api/internal/get_channel_status" % BASE_URL
GET_CHANNEL_STATUS_BULK_URL = "%s/api/internal/get_channel_status_bulk" % BASE_URL
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
    print('in ccserver_authenticate_user')

    ccserver_base_url = settings.DEFAULT_CONTENT_CURATION_SERVER
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

# (returns 403 if not authorized)



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


def get_channel_status(baruser, channel_id):
    """
        returns channel's status
    """
    return post_request(baruser, GET_CHANNEL_STATUS_URL, data={"channel_id": channel_id})


def get_channel_status_bulk(baruser, channel_ids):
    """
        returns channel's status
    """
    return post_request(baruser, GET_CHANNEL_STATUS_BULK_URL, data={"channel_ids": channel_ids})


def get_staged_diff(baruser, channel):
    pass
# api/internal/get_staged_diff_internal
# Returns a list of changes between the main tree and the staged tree (Includes date/time created, file size, # of each content kind, # of questions, and # of subtitles)
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

def compare_trees(baruser, channel):
    pass
# api/internal/compare_trees
# Returns a dict of new nodes and deleted nodes between either the staging tree or main tree and the previous tree (use staging flag to indicate whether to use staging or main)
# POST
# Header: ---
# Body:
# {
#     "channel_id": "{uuid.hex}",
#     "staging": boolean
# }
#
#
# {
#     "success" : True,
#     "new" : {
#         "{node_id}" : {
#              "title" : "{str}",
#              "kind" : "{str}",
#              "file_size" : {number}
#         },
#     },
#     "deleted" : {
#         "{node_id}" : {
#              "title" : "{str}",
#              "kind" : "{str}",
#              "file_size" : {number}
#         }
#     }
# }
#
# Example:
# {
#     "success" : True,
#     "new" : {
#         "aaa" : {
#              "title" : "Node Title",
#              "kind" : "topic",
#              "file_size" : 0
#         },
#         "bbb" : {
#              "title" : "Node Title 2",
#              "kind" : "audio",
#              "file_size" : 100
#         }
#     },
#     "deleted" : {
#         "ccc" : {
#              "title" : "Node Title 3",
#              "kind" : "video",
#              "file_size" : 999999
#         }
#     }
# }





def ccserver_get_topic_tree(run):
    data = []
    try:
        request = requests.post(
                "%s/api/internal/get_tree_data" % run.content_server,
                data=json.dumps({"channel_id" : run.channel.channel_id.hex,}),
                headers={'Authorization': 'Token %s' % run.started_by_user_token,
                         'Content-Type': 'application/json'})
        if request.ok:
            data = request.json().get("tree", [])
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

