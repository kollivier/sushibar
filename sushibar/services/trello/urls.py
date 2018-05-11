from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from .api import (ContentChannelSaveTrelloUrl,
                  TrelloAddChecklistItem,
                  TrelloMoveToFeedbackList,
                  ContentChannelFlagForQA,
                  TrelloNotifyCardChange,
                  TrelloSendComment,
                  TrelloMoveToDoneList,
                  TrelloMoveToPublishList)

urlpatterns = [
    # Save Trello URL to channel
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/save_trello_url/$',
        view=ContentChannelSaveTrelloUrl.as_view(),
        name='save_trello_url'),

    # Check card is on authorized board
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/add_item/$',
        view=TrelloAddChecklistItem.as_view(),
        name='trello_add_checklist_item'),

   	# Move card to Feedback Needed list
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/request_feedback/$',
        view=TrelloMoveToFeedbackList.as_view(),
        name='trello_request_feedback'),

   	# Move card to QA list and create QA sheet
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/flag_for_qa/$',
        view=ContentChannelFlagForQA.as_view(),
        name='trello_flag_channel_for_qa'),

    # Move card to DONE list
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/mark_as_done/$',
        view=TrelloMoveToDoneList.as_view(),
        name='trello_mark_channel_as_done'),

    # Move card to Publish list
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/flag_for_publish/$',
        view=TrelloMoveToPublishList.as_view(),
        name='trello_flag_channel_for_publish'),

    # WEBHOOK: Notify user when QA is done
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/card_moved/$',
        view=TrelloNotifyCardChange.as_view(),
        name='trello_notify_card_move'),

    # Send comment to Trello card
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/send_comment/$',
        view=TrelloSendComment.as_view(),
        name='trello_send_comment'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
