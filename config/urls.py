from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.views.generic import TemplateView
from django.views import defaults as default_views

from sushibar.dashboard.views import DashboardView, RunView, open_channel_page
from sushibar.users.forms import SushiBarAuthenticationForm

urlpatterns = [
    # Dashboard web views
    url(r'^$', DashboardView.as_view(), name='home'),
    url(r'^saved/$', DashboardView.as_view(view_saved=True), name='saved'),
    # TODO: this is a bad regex, use a better one that matches UUID4
    url(r'^runs/(?P<runid>[0-9A-Fa-f-]+)/$', RunView.as_view(), name='runs'),
    url(r'^channelpage/(?P<channel>[0-9A-Fa-f]+)/$', open_channel_page, name='open_channel_page'),
    url(r'^channels/(?P<channelid>[0-9A-Fa-f-]+)/$', RunView.as_view(search_by_channel=True), name='runs_for_channel'),
    url(r'^about/$', TemplateView.as_view(template_name='pages/about.html'), name='about'),
    url(r'^schedule/$', TemplateView.as_view(template_name='pages/schedule.html'), name='schedule'),

    # Django admin
    url(settings.ADMIN_URL, admin.site.urls),

    # Authentication and BarUser management
    url(r'^signin/$', auth_views.LoginView.as_view(
        template_name='auth/signin.html',
        authentication_form=SushiBarAuthenticationForm), name='sushibar_signin'),
    url(r'^signout/$', auth_views.LogoutView.as_view(template_name='auth/signed_out.html'), name='sushibar_signout'),
    url(r'^users/', include('sushibar.users.urls', namespace='users')),

    # SushiChef API endpoints
    url(r'^api/', include('sushibar.runs.urls')),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        url(r'^400/$', default_views.bad_request, kwargs={'exception': Exception('Bad Request!')}),
        url(r'^403/$', default_views.permission_denied, kwargs={'exception': Exception('Permission Denied')}),
        url(r'^404/$', default_views.page_not_found, kwargs={'exception': Exception('Page not Found')}),
        url(r'^500/$', default_views.server_error),
    ]
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            url(r'^__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns
    if 'rest_framework_swagger' in settings.INSTALLED_APPS:
        from rest_framework_swagger.views import get_swagger_view
        schema_view = get_swagger_view(title='Sushi Bar API')

        urlpatterns += [
            url(r'^apidocs/$', schema_view)
        ]