from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import BarUser
from sushibar.runs.models import ContentChannel
from sushibar.ccserverlib.services import get_user_channels


class UserDetailView(LoginRequiredMixin, DetailView):
    model = BarUser
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, *arg, **kwargs):
        context = super(UserDetailView, self).get_context_data(*arg, **kwargs)
        status, channels = get_user_channels(self.get_object())
        context['channels'] = []
        if status == 'success':
            channel_ids = [cid.hex for cid in ContentChannel.objects.values_list("channel_id", flat=True)]

            for channel in channels:
                if channel.get('id') in channel_ids:
                    context['channels'].append(channel)
        return context


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return "/"


class UserUpdateView(LoginRequiredMixin, UpdateView):

    fields = ['name', ]

    # we already imported BarUser in the view code above, remember?
    model = BarUser

    # send the user back to their own page after a successful update
    def get_success_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})

    def get_object(self):
        # Only get the BarUser record for the user making the request
        return BarUser.objects.get(username=self.request.user.username)


class UserListView(LoginRequiredMixin, ListView):
    model = BarUser
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'
