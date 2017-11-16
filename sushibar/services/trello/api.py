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
from sushibar.services.trello.config import TRELLO_RUN_LIST_ID, TRELLO_QA_LIST_ID

TRELLO_API_KEY = settings.TRELLO_API_KEY
TRELLO_TOKEN = settings.TRELLO_TOKEN
TRELLO_BOARD = settings.TRELLO_BOARD
TRELLO_REGEX = r'https{0,1}:\/\/trello.com\/c\/([0-9A-Za-z]{8})\/.*'

# Trello Requests
def post_request(url, data=None):
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.post(url, data=data)

def put_request(url, data=None):
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.put(url, data=data)

def get_request(url, data=None):
    data = data or {}
    data.update({"key": TRELLO_API_KEY, "token": TRELLO_TOKEN})
    return requests.get("{}?{}".format(url, urllib.parse.urlencode(data)))

def trello_move_card(channel_id, list_id):
    channel = ContentChannel.objects.get(channel_id=channel_id)
    card_id = extract_id(channel.trello_url)
    move_url = "https://api.trello.com/1/cards/{}/idList".format(card_id)
    response = put_request(move_url, data={"value": list_id})
    response.raise_for_status()
    return response

def trello_move_card_to_run_list(channel_id):
    return trello_move_card(channel_id, TRELLO_RUN_LIST_ID)

def trello_create_webhook(request, channel, card_id):
    domain = request.META.get('HTTP_ORIGIN') or \
            "http://{}".format(request.get_host() or \
            get_current_site(request).domain)
    callback = "{}/services/trello/{}/card_moved/".format(domain, channel.channel_id.hex)
    url = 'https://api.trello.com/1/webhooks/'
    response = post_request(url, data={'idModel': card_id, 'description': "card-update", 'callbackURL': callback})
    response.raise_for_status()
    channel.trello_webhook_url = callback
    channel.save()

def trello_get_list_name(channel):
    card_id = extract_id(channel.trello_url)
    card_url = "https://api.trello.com/1/cards/{}".format(card_id)
    response = get_request(card_url)
    list_id = json.loads(response.content)['idList']
    list_url = "https://api.trello.com/1/lists/{}".format(list_id)
    list_response = get_request(list_url)
    return json.loads(list_response.content)['name']

def extract_id(url):
    match = re.search(TRELLO_REGEX, url)
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
            channel.trello_url = None
            channel.trello_webhook_url = None
            channel.save()
            return HttpResponse("Saved Trello URL")

        # Check the url is formatted correctly
        card_id = extract_id(trello_url)
        if not card_id:
            return HttpResponseBadRequest("Invalid id")

        # Check the card is from the sushibar board
        response = self.get_request("https://api.trello.com/1/cards/{}".format(card_id))
        if response.status_code == 200:
            trello_data = json.loads(response.content.decode('utf-8'))
            if trello_data['idBoard'] != TRELLO_BOARD:
                return HttpResponseForbidden("Not authorized to access card")

            # Save the url if it passes tests
            channel.trello_url = trello_url
            channel.save()
            # trello_create_webhook(request, channel, trello_data['id'])
            return HttpResponse(response.content)
        else:
            return HttpResponseBadRequest(response.content.capitalize())

class TrelloAddChecklistItem(TrelloBaseView):
    """
    Save trello url to channel
    """
    checklist_url = "https://api.trello.com/1/cards/{}/checklists"

    def post(self, request, channel_id):
        """
        Handle "add checklist item" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        # Get any checklists that are on the card
        card_id = extract_id(channel.trello_url)
        checklist_response = self.get_request(self.checklist_url.format(card_id))
        checklists = json.loads(checklist_response.content.decode('utf-8'))
        checklist = None

        # If there are no checklists, create a new one
        # Otherwise, add to first list on the board
        if not len(checklists):
            create_response = self.post_request(self.checklist_url.format(card_id), data={"name": "Channel TODO"})
            if create_response.status_code != 200:
                return HttpResponseBadRequest(create_response.content.capitalize())
            checklist = json.loads(create_response.content)
        else:
          checklist = checklists[0]

        # Format message with timestamp
        message = request.data['item']
        current_timestamp = format_datetime(datetime.datetime.now())
        formatted_message = "{} (requested {})".format(message, current_timestamp)

        # If item is already in checklist, update the time and uncheck it
        # Otherwise, create a new item
        match = next((i for i in checklist['checkItems'] if i['name'].startswith(message)), None)
        if match:
            update_url = "https://api.trello.com/1/cards/{}/checkItem/{}".format(card_id, match['id'])
            response = self.put_request(update_url, data={"name": formatted_message, "state": "incomplete"})
            if response.status_code != 200:
                return HttpResponseBadRequest(response.content.capitalize())
        else:
            create_url = "https://api.trello.com/1/checklists/{}/checkItems".format(checklist['id'])
            response = self.post_request(create_url, data={"name": formatted_message, "checked": "false"})
            if response.status_code != 200:
                return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse("Added checklist item '{}'".format(formatted_message))

class TrelloMoveToQAList(TrelloBaseView):
    """
    Move card to QA list
    """
    move_url = "https://api.trello.com/1/cards/{}/idList"

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
        response = self.put_request(self.move_url.format(card_id), {"value": TRELLO_QA_LIST_ID})


        list_response = self.get_request("https://api.trello.com/1/lists/{}".format(TRELLO_QA_LIST_ID))

        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse(list_response.content)


class TrelloNotifyCardMove(TrelloBaseView):
    """
    Move card to QA list
    """
    move_url = "https://api.trello.com/1/cards/{}/idList"

    def post(self, request, channel_id):
        """
        Handle "add checklist item" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            return HttpResponseNotFound("Channel not found")

        # Get any checklists that are on the card
        card_id = extract_id(channel.trello_url)
        response = self.put_request(self.move_url.format(card_id), {"value": TRELLO_QA_LIST_ID})

        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse("Flagged channel to QA list")

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
        response = self.put_request(self.move_url.format(card_id), {"value": TRELLO_QA_LIST_ID})

        if response.status_code != 200:
            return HttpResponseBadRequest(response.content.capitalize())

        return HttpResponse("Flagged channel to QA list")

    def get(self, request, channel_id):
        return HttpResponse("Success!")
