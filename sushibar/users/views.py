from django.core.urlresolvers import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from django.contrib.auth.mixins import LoginRequiredMixin

from .models import BarUser


class UserDetailView(LoginRequiredMixin, DetailView):
    model = BarUser
    # These next two lines tell the view to index lookups by username
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, *arg, **kwargs):
        context = super(UserDetailView, self).get_context_data(*arg, **kwargs)
        context['user_info_dict'] = self.get_object().__dict__
        print(context)
        return context


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse('users:detail',
                       kwargs={'username': self.request.user.username})


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
