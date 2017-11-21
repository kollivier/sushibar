import re
from django import forms
from sushibar.runs.models import ContentChannel
from sushibar.runs.utils import calculate_channel_id
from sushibar.services.trello.api import validate_trello_card
from sushibar.services.trello.config import TRELLO_REGEX

GITHUB_REGEX = r'https?://github.com/learningequality/.+'
GOOGLE_REGEX = r'https?://docs\.google\.com/document/d/.+'

class ChannelCreateForm(forms.Form):
    name = forms.CharField(max_length=200, required=True, label='Name',
                widget=forms.TextInput(attrs={'placeholder': 'Enter channel name...'}))
    domain = forms.CharField(max_length=200, required=True, label='Domain',
                widget=forms.TextInput(attrs={'placeholder': 'Enter channel domain...'}))
    source_id = forms.CharField(max_length=200, required=True, label='Source ID',
                widget=forms.TextInput(attrs={'placeholder': 'Enter channel source ID...'}))
    chef_repo = forms.CharField(max_length=200, required=True, label='Chef Repo',
                widget=forms.TextInput(attrs={'placeholder': 'Copy link to chef github repository..'}))
    spec_sheet_url = forms.CharField(max_length=200, required=True, label='Spec Sheet',
                widget=forms.TextInput(attrs={'placeholder': 'Copy link to spec sheet...'}))
    trello_url = forms.CharField(max_length=200, required=True, label='Trello Card',
                widget=forms.TextInput(attrs={'placeholder': 'Copy link to Trello card...'}))

    def clean(self):
        cleaned_data = super(ChannelCreateForm, self).clean()

        if 'domain' in self.cleaned_data and 'source_id' in self.cleaned_data:
            self.cleaned_data['channel_id'] = calculate_channel_id(self.cleaned_data['source_id'], self.cleaned_data['domain'])

            # Check channel id doesn't already exist
            if ContentChannel.objects.filter(channel_id=self.cleaned_data['channel_id']).exists():
                self.add_error('domain', 'Channel with domain and source ID already exists')

        # Make sure Trello URL is valid and user can access Trello card
        if 'trello_url' in self.cleaned_data:
            if not re.search(TRELLO_REGEX, self.cleaned_data['trello_url']):
                self.add_error('trello_url', 'Invalid Trello URL')
            elif not validate_trello_card(self.cleaned_data['trello_url']):
                self.add_error('trello_url', 'Cannot access Trello card')

        # Make sure google spec sheet is valid:
        if 'spec_sheet_url' in self.cleaned_data and not re.search(GOOGLE_REGEX, self.cleaned_data['spec_sheet_url']):
            self.add_error('spec_sheet_url', 'Invalid spec sheet URL')

        # Make sure github URL is valid:
        if 'chef_repo' in self.cleaned_data and not re.search(GITHUB_REGEX, self.cleaned_data['chef_repo']):
            self.add_error('chef_repo', 'Invalid github repository')

        return self.cleaned_data
