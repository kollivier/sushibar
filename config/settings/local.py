"""
Local settings

- Run in Debug mode

- Use console backend for emails

- Add Django Debug Toolbar
- Add django-extensions as app
"""

from .base import *  # noqa

# DEBUG
# ------------------------------------------------------------------------------
DEBUG = get_env('DJANGO_DEBUG', default=True)
TEMPLATES[0]['OPTIONS']['debug'] = DEBUG

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Note: This key only used for development and testing.
SECRET_KEY = get_env('DJANGO_SECRET_KEY', default='@)Vj<pBjh6wbdJ;Gh7:V)_sypdv`UGpET&1kyy90F)iV,6KG@O')

# Mail settings
# ------------------------------------------------------------------------------

EMAIL_PORT = 1025

EMAIL_HOST = 'localhost'
EMAIL_BACKEND = get_env('DJANGO_EMAIL_BACKEND',
                    default='django.core.mail.backends.console.EmailBackend')


# CACHING
# ------------------------------------------------------------------------------
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': ''
    }
}

# django-debug-toolbar
# ------------------------------------------------------------------------------
MIDDLEWARE += ['debug_toolbar.middleware.DebugToolbarMiddleware', ]
INSTALLED_APPS += [
    'debug_toolbar',
    'rest_framework_swagger',
]

INTERNAL_IPS = ['127.0.0.1', '10.0.2.2', ]


import socket
import os

# tricks to have debug toolbar when developing with docker
if os.environ.get('USE_DOCKER') == 'yes':
    ip = socket.gethostbyname(socket.gethostname())
    INTERNAL_IPS += [ip[:-1] + '1']

DEBUG_TOOLBAR_CONFIG = {
    'DISABLE_PANELS': [
        'debug_toolbar.panels.redirects.RedirectsPanel',
    ],
    'SHOW_TEMPLATE_CONTEXT': True,
}


# django-extensions
# ------------------------------------------------------------------------------
INSTALLED_APPS += ['django_extensions', ]


# TESTING
# ------------------------------------------------------------------------------
TEST_RUNNER = 'django.test.runner.DiscoverRunner'


# Your local stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

MEDIA_ROOT = join(ROOT_DIR, 'local_media')


# Settings for storing progress in redis  (used for sushichef MMVP)
MMVP_REDIS_HOST = 'localhost'
MMVP_REDIS_PORT = 6379
MMVP_REDIS_DB = 0
MMVP_REDIS_TEST_DB = 1

