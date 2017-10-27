from django.conf.urls import url
from rest_framework.urlpatterns import format_suffix_patterns

from .api import ContentChannelSaveTrelloUrl, TrelloAddChecklistItem

urlpatterns = [
    # Save Trello URL to channel
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/save_trello_url/$',
        view=ContentChannelSaveTrelloUrl.as_view(),
        name='save_trello_url'),

    # Check card is on authorized board
    url(regex=r'(?P<channel_id>[0-9A-Fa-f-]+)/add_item/$',
        view=TrelloAddChecklistItem.as_view(),
        name='trello_add_checklist_item'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
