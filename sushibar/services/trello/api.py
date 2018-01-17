import datetime
import json
import re
import requests
import urllib

from django.conf import settings
from django.contrib.sites.shortcuts import get_current_site
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotFound, HttpResponseForbidden
from rest_framework.response import Response
from rest_framework.views import APIView

from sushibar.runs.models import ContentChannel
from sushibar.services.trello import config

TRELLO_API_KEY = settings.TRELLO_API_KEY
TRELLO_TOKEN = settings.TRELLO_TOKEN
TRELLO_BOARD = settings.TRELLO_BOARD
TRELLO_URL = "https://api.trello.com/1/"

# Trello Requests
def post_request(endpoint, data=None):
    url = "{}{}".format(TRELLO_URL, endpoint)
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.post(url, data=data)

def put_request(endpoint, data=None):
    url = "{}{}".format(TRELLO_URL, endpoint)
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.put(url, data=data)

def get_request(endpoint, data=None):
    url = "{}{}".format(TRELLO_URL, endpoint)
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.get("{}?{}".format(url, urllib.parse.urlencode(data)))

def delete_request(endpoint, data=None):
    url = "{}{}".format(TRELLO_URL, endpoint)
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.delete("{}?{}".format(url, urllib.parse.urlencode(data)))

def trello_move_card(channel, list_id):
    card_id = extract_id(channel.trello_url)
    response = put_request("cards/{}/idList".format(card_id), data={"value": list_id})
    response.raise_for_status()
    return response

def trello_move_card_to_run_list(channel):
    return trello_move_card(channel, config.TRELLO_RUN_LIST_ID)

def trello_move_card_to_qa_list(channel):
    return trello_move_card(channel, config.TRELLO_QA_LIST_ID)

def trello_move_card_to_done_list(channel):
    return trello_move_card(channel, config.TRELLO_DONE_LIST_ID)


def trello_create_webhook(request, channel, card_id):

    # Delete webhook if no channels are using it
    if channel.trello_webhook_id and not ContentChannel.objects.filter(trello_webhook_id=channel.trello_webhook_id).exists():
        delete_request("webhooks/{}".format(channel.trello_webhook_id))

    domain = settings.LOCAL_DEV_DEFAULT_DOMAIN or request.META.get('HTTP_ORIGIN') or \
            "http://{}".format(request.get_host() or \
            get_current_site(request).domain)
    callback = "{}/services/trello/{}/card_moved/".format(domain, channel.channel_id.hex)
    channel_with_same_card = ContentChannel.objects.filter(trello_webhook_url=callback).exclude(trello_webhook_id=None).first()
    response = post_request('webhooks/', data={'idModel': card_id, 'description': "card-update", 'callbackURL': callback})

    if channel_with_same_card:
        channel.trello_webhook_url = channel_with_same_card.trello_webhook_url
        channel.trello_webhook_id = channel_with_same_card.trello_webhook_id

    # Raises 400 when webhook combination already exists
    elif response.status_code == 400:
        channel.trello_webhook_url = callback
    else:
        response.raise_for_status()
        channel.trello_webhook_url = callback
        channel.trello_webhook_id = json.loads(response.content.decode('utf-8'))['id']

    channel.save()


def trello_get_list_name(channel):
    card_id = extract_id(channel.trello_url)
    response = get_request("cards/{}".format(card_id))
    trello_data = json.loads(response.content.decode('utf-8'))
    list_id = trello_data['idList']
    list_response = get_request("lists/{}".format(list_id))
    return trello_data['name']

def trello_get_due_date(channel):
    card_id = extract_id(channel.trello_url)
    response = get_request("cards/{}".format(card_id))
    trello_data = json.loads(response.content.decode('utf-8'))
    import pdb; pdb.set_trace()
    list_id = trello_data['idList']
    list_response = get_request("lists/{}".format(list_id))
    return trello_data['name']

def validate_trello_card(trello_url):
    card_id = extract_id(trello_url)
    response = get_request("cards/{}".format(card_id))
    if response.status_code == 200:
        trello_data = json.loads(response.content.decode('utf-8'))
        if trello_data['idBoard'] != TRELLO_BOARD:
            return False
    return response.status_code == 200

def trello_add_card_to_channel(request, channel, trello_url):

    # Check the url is formatted correctly
    card_id = extract_id(trello_url)
    if not card_id:
        return HttpResponseBadRequest("Invalid id")

    # Check the card is from the sushibar board
    response = get_request("cards/{}".format(card_id))
    if response.status_code == 200:
        trello_data = json.loads(response.content.decode('utf-8'))
        if trello_data['idBoard'] != TRELLO_BOARD:
            return HttpResponseForbidden("Not authorized to access card")

        # Save the url if it passes tests
        channel.trello_url = trello_url
        channel.save()
        trello_create_webhook(request, channel, trello_data['id'])
        return HttpResponse(response.content)
    else:
        return HttpResponseBadRequest(response.content.capitalize())

def trello_add_checklist_item(channel, message):
     # Get any checklists that are on the card
    card_id = extract_id(channel.trello_url)
    checklist_response = get_request("cards/{}/checklists".format(card_id))
    checklists = json.loads(checklist_response.content.decode('utf-8'))

    # If there are no checklists, create a new one
    # Otherwise, add to first list on the board
    checklist = next((c for c in checklists if c['name'] == config.TRELLO_CHECKLIST_NAME), None)
    if not checklist:
        create_response = post_request("cards/{}/checklists".format(card_id), data={"name": config.TRELLO_CHECKLIST_NAME})
        if create_response.status_code != 200:
            return HttpResponseBadRequest(create_response.content.capitalize())
        checklist = json.loads(create_response.content.decode('utf-8'))

    # Format message with timestamp
    current_timestamp = format_datetime(datetime.datetime.now())
    formatted_message = "{} (requested {})".format(message, current_timestamp)

    # If item is already in checklist, update the time and uncheck it
    # Otherwise, create a new item
    match = next((i for i in checklist['checkItems'] if i['name'].startswith(message)), None)
    if match:
        update_url = "cards/{}/checkItem/{}".format(card_id, match['id'])
        response = put_request(update_url, data={"name": formatted_message, "state": "incomplete"})
        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())
    else:
        create_url = "checklists/{}/checkItems".format(checklist['id'])
        response = post_request(create_url, data={"name": formatted_message, "checked": "false"})
        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

    return HttpResponse("Added checklist item '{}'".format(formatted_message))

def trello_add_channel_link(channel):
    # Check if channel is already linked to card
    card_id = extract_id(channel.trello_url)
    card_endpoint = "cards/{}".format(card_id)
    card_response = get_request(card_endpoint)

    # Return bad request if getting card fails
    if card_response.status_code != 200:
        return HttpResponseBadRequest(card_response.content.capitalize())

    description = json.loads(card_response.content.decode('utf-8')).get('desc')
    channel_link = "Channel: [%s](%s/%s/edit)" % (channel.name, channel.default_content_server, channel.channel_id.hex)

    # If the channel link isn't in the description, append it
    if description and channel_link not in description:
        response = put_request(card_endpoint, data={'desc': "%s\n%s" % (description, channel_link)})
        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())
    return HttpResponse("Updated description with " + channel_link)

def extract_id(url):
    match = re.search(config.TRELLO_REGEX, url)
    return match and match.group(1)

def format_datetime(dt):
    return dt.strftime("%b %d, %Y at %I:%M%p")

class TrelloBaseView(APIView):

    def post_request(self, url, data=None):
        """
        Set up all POST requests to Trello's API
        """
        return post_request(url, data=data)

    def put_request(self, url, data=None):
        """
        Set up all PUT requests to Trello's API
        """
        return put_request(url, data=data)

    def get_request(self, url, data=None):
        """
        Set up all GET requests to Trello's API
        """
        return get_request(url, data=data)


class ContentChannelSaveTrelloUrl(TrelloBaseView):
    """
    Save trello url to channel
    """
    def post(self, request, channel_id):
        """
        Handle "save trello url " ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        trello_url = request.data['trello_url']

        # Allow user to remove trello url from channels
        if trello_url == "":
            # Delete webhook if no channels are using it
            if channel.trello_webhook_id and not ContentChannel.objects.filter(trello_webhook_id=channel.trello_webhook_id).exists():
                delete_request("webhooks/{}".format(channel.trello_webhook_id))
            channel.trello_url = None
            channel.trello_webhook_url = None
            channel.trello_webhook_id = None
            channel.run_needed = False
            channel.changes_needed = False
            channel.save()
            return HttpResponse("Saved Trello URL")
        return trello_add_card_to_channel(request, channel, trello_url)

class TrelloAddChecklistItem(TrelloBaseView):
    """
    Add item to Trello card checklist
    """

    def post(self, request, channel_id):
        """
        Handle "add checklist item" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        return trello_add_checklist_item(channel, request.data['item'])

class TrelloBaseMoveList(TrelloBaseView):
    """
    Move card to list
    """
    list_id = None

    def put(self, request, channel_id):
        """
        Handle "add checklist item" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        # Get any checklists that are on the card
        card_id = extract_id(channel.trello_url)
        response = self.put_request("cards/{}/idList".format(card_id), {"value": self.list_id})

        list_response = self.get_request("lists/{}".format(self.list_id))

        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse(list_response.content)

class TrelloMoveToQAList(TrelloBaseMoveList):
    """
    Move card to QA list
    """
    list_id = config.TRELLO_QA_LIST_ID


class TrelloMoveToDoneList(TrelloBaseMoveList):
    """
    Move card to DONE list
    """
    list_id = config.TRELLO_DONE_LIST_ID

class TrelloMoveToPublishList(TrelloBaseMoveList):
    """
    Move card to DONE list
    """
    list_id = config.TRELLO_PUBLISH_LIST_ID

class TrelloNotifyCardChange(TrelloBaseView):
    """
    Update status of channel based on Trello list
    """

    def handle_change(self, request, channel_id):
        """
        Handle card change from Trello (webhook)
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        try:
            request_data = request.data['action']['data']

            # Card has been moved
            if request_data.get('listAfter'):
                self.handle_move(request_data, channel)

            # Card's due date has been updated
            elif request_data.get('card') and request_data['card'].get('due'):
                self.handle_due_date(request_data, channel)

        except KeyError:
            pass

        return HttpResponse("")

    def handle_due_date(self, request_data, channel):
        channel.due_date = request_data['card']['due']
        channel.save()

    def handle_move(self, request_data, channel):
        new_list = request_data['listAfter']['id']
        old_list = request_data['listBefore']['id']

        # Only set if chef is not in initial stage
        if old_list != config.TRELLO_READY_LIST_ID:
            channel.run_needed = new_list == config.TRELLO_RUN_LIST_ID
            channel.changes_needed = new_list == config.TRELLO_DEVELOPMENT_LIST_ID
        channel.new_run_complete = False
        channel.save()

        # TODO: Add logic for emailing/pinging developer here

    def post(self, request, channel_id):
        return self.handle_change(request, channel_id)

    def put(self, request, channel_id):
        return self.handle_change(request, channel_id)

    def head(self, request, channel_id):
        return HttpResponse("Success!")


class TrelloSendComment(TrelloBaseView):
    """
    Send comment to Trello card
    """

    def post(self, request, channel_id):
        """
        Handle card moves from Trello (webhook)
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        comment = request.data['comment']
        card_id = extract_id(channel.trello_url)

        response = self.post_request('cards/{}/actions/comments'.format(card_id), data={'text': comment})

        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse("")
