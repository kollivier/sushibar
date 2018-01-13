
from datetime import timedelta
import json

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponseBadRequest
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from rest_framework import permissions, status
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from channels import Group

from .models import ContentChannel, ContentChannelRun, ChannelRunStage
from .serializers import ContentChannelSerializer
from .serializers import ContentChannelRunSerializer
from .serializers import ChannelRunStageCreateSerializer, ChannelRunStageSerializer
from .serializers import ChannelRunProgressSerializer
from .serializers import ContentChannelSaveToProfileSerializer
from .serializers import ChannelControlSerializer
from .utils import load_tree_for_channel, set_run_options, calculate_channel_id

from sushibar.services.trello.api import trello_move_card_to_qa_list, trello_add_checklist_item
from sushibar.services.google.api import create_qa_sheet

# REDIS connection #############################################################
import redis
REDIS = redis.StrictRedis(host=settings.MMVP_REDIS_HOST,
                          port=settings.MMVP_REDIS_PORT,
                          db=settings.MMVP_REDIS_DB,
                          charset="utf-8",
                          decode_responses=True)



# CONTENT CHANNELS #############################################################

class ContentChannelListCreate(ListCreateAPIView):
    """
    List all content channels or create a new channel.
    """
    queryset = ContentChannel.objects.all()
    serializer_class = ContentChannelSerializer

class ContentChannelDetail(RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, or delete a content channel instance.
    """
    queryset = ContentChannel.objects.all()
    serializer_class = ContentChannelSerializer
    lookup_field =  'channel_id'


class ContentChannelSaveToProfile(APIView):
    """
    Save a content channel to the user profile.
    """
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    def post(self, request, channel_id, format=None):
        """
        Handle "save to profile" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            raise Http404
        serializer = ContentChannelSaveToProfileSerializer(data=request.data)
        if serializer.is_valid():
            wants_saved = serializer.data['save_channel_to_profile']
            channel_followers = channel.followers.all()
            if wants_saved and request.user not in channel_followers:
                channel.followers.add(request.user)
                channel.save()
            if not wants_saved and request.user in channel_followers:
                channel.followers.remove(request.user)
                channel.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContentChannelSaveTrelloUrl(APIView):
    """
    Save trello url to channel
    """
    def post(self, request, channel_id, format=None):
        """
        Handle "save trello url " ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            raise Http404
        serializer = ContentChannelSaveTrelloUrlSerializer(data=request.data)
        if serializer.is_valid():
            trello_url = serializer.data['trello_url']
            channel.trello_url = trello_url
            channel.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContentChannelFlagForQA(APIView):
    """
    Flag channel for QA
    """
    def post(self, request, channel_id, format=None):
        """
        Handle "flag_for_qa" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            raise Http404

        # TODO: Don't generate if channel.qa_sheet_id already exists!
        if not channel.qa_sheet_id:
            channel.qa_sheet_id = create_qa_sheet(channel.name + " QA")
            channel.save()

        message = "Fill out [QA sheet]({})".format("https://docs.google.com/spreadsheets/d/{}/edit".format(channel.qa_sheet_id))
        trello_response = trello_add_checklist_item(channel, message)

        response = trello_move_card_to_qa_list(channel)
        response.raise_for_status()

        return Response({"success": True, "qa_sheet_id": channel.qa_sheet_id}, status=status.HTTP_200_OK)


class ContentChannelDelete(APIView):
    """
    Delete channel from sushibar
    """
    def post(self, request, channel_id, format=None):
        """
        Handle "delete_channel" ajax calls.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            raise Http404

        if channel.runs.exists():
            raise HttpResponseBadRequest("Cannot delete activated channels")

        channel.delete()
        return Response({"message": "Deleted channel {}".format(channel_id)}, status=status.HTTP_200_OK)

# CHANNEL RUNS #################################################################

class RunsForContentChannelList(APIView):
    """
    List all runs for a given content channels.
    """
    def get(self, request, channel_id, format=None):
        """
        List all runs for content channel `channel_id`.
        """
        try:
            channel = ContentChannel.objects.get(channel_id=channel_id)
        except ContentChannel.DoesNotExist:
            raise Http404
        serializer = ContentChannelRunSerializer(channel.runs, many=True)
        return Response(serializer.data)

class ContentChannelRunListCreate(APIView):
    """
    Create a new channel run or list all channel runs.
    """
    def get(self, request, format=None):
        """
        List all content channel runs.
        """
        runs = ContentChannelRun.objects.all()
        serializer = ContentChannelRunSerializer(runs, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
        """
        Create a new channel run.
        """
        serializer = ContentChannelRunSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContentChannelRunDetail(APIView):
    """
    Retrieve, update, or delete the data associated with a channel run.
    """
    def get_object(self, run_id):
        try:
            return ContentChannelRun.objects.get(run_id=run_id)
        except ContentChannelRun.DoesNotExist:
            raise Http404

    def get(self, request, run_id, format=None):
        run = self.get_object(run_id)
        serializer = ContentChannelRunSerializer(run)
        return Response(serializer.data)

    def patch(self, request, run_id, format=None):
        run = self.get_object(run_id)
        serializer = ContentChannelRunSerializer(run, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, run_id, format=None):
        run = self.get_object(run_id)
        run.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)



# CHANNEL RUN STAGES ###########################################################

class ChannelRunStageListCreate(APIView):
    """
    List and create the stages for the ContentChannelRun `run_id`.
    """
    def get(self, request, run_id, format=None):
        """
        List all stages for a channel run.
        """
        try:
            run = ContentChannelRun.objects.get(run_id=run_id)
        except ContentChannelRun.DoesNotExist:
            raise Http404
        stages = ChannelRunStage.objects.filter(run=run)
        serializer = ChannelRunStageSerializer(stages, many=True)
        return Response(serializer.data)

    def post(self, request, run_id, format=None):
        """
        POST: notify sushibar that `run_id` sushichef has finished a stage.
        """
        create_serializer = ChannelRunStageCreateSerializer(data=request.data)
        if create_serializer.is_valid():
            assert run_id == create_serializer.data['run_id'], 'run_id mismatch in HTTP POST'
            duration = timedelta(seconds=create_serializer.data['duration'])
            server_time = timezone.now()
            calculated_started = server_time - duration
            run_stage = ChannelRunStage.objects.create(run_id=run_id,
                                                       name=create_serializer.data['stage'],
                                                       started=calculated_started,
                                                       finished=server_time,
                                                       duration=duration)
            if run_stage.name == 'COMPLETED':
                run = ContentChannelRun.objects.get(run_id=run_id)
                load_tree_for_channel(run)
                set_run_options(run)
                run.channel.new_run_complete = True
                run.channel.save()

            # TODO: cleanup dict in redis under name `run_id` on FINISHED stage
            response_serializer = ChannelRunStageSerializer(run_stage)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(create_serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# CHANNEL RUN PROGRESS #########################################################
# Temporary hack for MMVP --- manually store/retrieve progress in redis
# TODO: repalce with channels implementation for final version

class ChannelRunProgressEndpoints(APIView):

    def get(self, request, run_id, format=None):
        """
        Return current progress from redis.
        """
        progress_data_dict = REDIS.hgetall(run_id)
        serializer = ChannelRunProgressSerializer(progress_data_dict)
        return Response(serializer.data)

    def post(self, request, run_id, format=None):
        """
        Store progress update to redis.
        """
        serializer = ChannelRunProgressSerializer(data=request.data)
        if serializer.is_valid():
            REDIS.hmset(run_id, serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



# DAEMONIZED SUSHICHEF CONTROL #################################################

class ChannelControlEndpoints(APIView):
    permission_classes = (permissions.IsAdminUser,)

    def post(self, request, channel_id, format=None):
        """
        Send command+args+options to sushi chef daeamon hooked up for the channel.
        """
        serializer = ChannelControlSerializer(data=request.data)
        if serializer.is_valid():
            group = Group('control-' + channel_id)
            msg_dict = dict(
                command=serializer.data['command'],
                args=serializer.data['args'],
                options=serializer.data['options'],
            )
            msg_text = json.dumps(msg_dict)
            group.send({'text': msg_text})
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
