"""
Production configurations

  - Use Redis for cache


"""

from .base import *  # noqa

# SECRET CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Raises ImproperlyConfigured exception if DJANGO_SECRET_KEY not in os.environ
SECRET_KEY = get_env('DJANGO_SECRET_KEY')


# This ensures that Django will be able to detect a secure connection
# properly on Heroku.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# SECURITY CONFIGURATION
# ------------------------------------------------------------------------------
# See https://docs.djangoproject.com/en/dev/ref/middleware/#module-django.middleware.security
# and https://docs.djangoproject.com/en/dev/howto/deployment/checklist/#run-manage-py-check-deploy
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# SECURE_SSL_REDIRECT = bool(get_env('DJANGO_SECURE_SSL_REDIRECT', default=True)
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = False    # provides no benefts + we need CSRF cookie to make ajax requests
X_FRAME_OPTIONS = 'DENY'
DEBUG = get_env('DJANGO_DEBUG', False)


# SITE CONFIGURATION
# ------------------------------------------------------------------------------
# Hosts/domain names that are valid for this site
# See https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = get_env('DJANGO_ALLOWED_HOSTS', default='sushibar.learningequality.org').split(',')
# END SITE CONFIGURATION

INSTALLED_APPS += ['gunicorn', ]


# STORAGE CONFIGURATION
# ------------------------------------------------------------------------------
# Uploaded Media Files
# ------------------------
# See: http://django-storages.readthedocs.io/en/latest/index.html
# INSTALLED_APPS += ['storages', ]
# AWS_ACCESS_KEY_ID = get_env('DJANGO_AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = get_env('DJANGO_AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = get_env('DJANGO_AWS_STORAGE_BUCKET_NAME')
# AWS_AUTO_CREATE_BUCKET = True
# AWS_QUERYSTRING_AUTH = False
# AWS_S3_CALLING_FORMAT = OrdinaryCallingFormat()
#
# # AWS cache settings, don't change unless you know what you're doing:
# AWS_EXPIRY = 60 * 60 * 24 * 7

# TODO See: https://github.com/jschneier/django-storages/issues/47
# Revert the following and use str after the above-mentioned bug is fixed in
# either django-storage-redux or boto
# control = 'max-age=%d, s-maxage=%d, must-revalidate' % (AWS_EXPIRY, AWS_EXPIRY)
# AWS_HEADERS = {
#     'Cache-Control': bytes(control, encoding='latin-1')
# }

# URL that handles the media served from MEDIA_ROOT, used for managing
# stored files.

#  See:http://stackoverflow.com/questions/10390244/
# from storages.backends.s3boto import S3BotoStorage
# StaticRootS3BotoStorage = lambda: S3BotoStorage(location='static')
# MediaRootS3BotoStorage = lambda: S3BotoStorage(location='media')
# DEFAULT_FILE_STORAGE = 'config.settings.production.MediaRootS3BotoStorage'

# MEDIA_URL = 'https://s3.amazonaws.com/%s/media/' % AWS_STORAGE_BUCKET_NAME

# Static Assets
# # ------------------------

STATIC_ROOT = '/static'

# STATIC_ROOT = join(BASE_DIR, 'djstatic')
# STATICFILES_FINDERS = [
#     'django.contrib.staticfiles.finders.FileSystemFinder',
#     'django.contrib.staticfiles.finders.AppDirectoriesFinder',
# ]
# STATIC_URL = '/static/djstatic/'

# STATIC_URL = 'https://s3.amazonaws.com/%s/static/' % AWS_STORAGE_BUCKET_NAME
# STATICFILES_STORAGE = 'config.settings.production.StaticRootS3BotoStorage'
# See: https://github.com/antonagestam/collectfast
# For Django 1.7+, 'collectfast' should come before
# 'django.contrib.staticfiles'
# AWS_PRELOAD_METADATA = True
# INSTALLED_APPS = ['collectfast', ] + INSTALLED_APPS


# EMAIL
# ------------------------------------------------------------------------------
DEFAULT_FROM_EMAIL = get_env('DJANGO_DEFAULT_FROM_EMAIL',
                         default='sushibar <noreply@sushibar.learningequality.org>')
EMAIL_SUBJECT_PREFIX = get_env('DJANGO_EMAIL_SUBJECT_PREFIX', default='[sushibar]')
SERVER_EMAIL = get_env('DJANGO_SERVER_EMAIL', default=DEFAULT_FROM_EMAIL)

# Anymail with Mailgun
# INSTALLED_APPS += ['anymail', ]
# ANYMAIL = {
#     'MAILGUN_API_KEY': get_env('DJANGO_MAILGUN_API_KEY'),
#     'MAILGUN_SENDER_DOMAIN': get_env('MAILGUN_SENDER_DOMAIN')
# }
# EMAIL_BACKEND = 'anymail.backends.mailgun.MailgunBackend'

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See:
# https://docs.djangoproject.com/en/dev/ref/templates/api/#django.template.loaders.cached.Loader
TEMPLATES[0]['OPTIONS']['loaders'] = [
    ('django.template.loaders.cached.Loader', [
        'django.template.loaders.filesystem.Loader',
        'django.template.loaders.app_directories.Loader',]),
]


# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
DATABASES['default']['HOST'] = 'postgres'  # hostname resolved inside `sushibar_default` network


# CACHING
# ------------------------------------------------------------------------------

REDIS_LOCATION = '{0}/{1}'.format(get_env('REDIS_URL', default='redis://127.0.0.1:6379'), 0)
# Heroku URL does not pass the DB number, so we parse it in
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_LOCATION,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'IGNORE_EXCEPTIONS': True,  # mimics memcache behavior.
                                        # http://niwinz.github.io/django-redis/latest/#_memcached_exceptions_behavior
        }
    }
}


# LOGGING CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#logging
# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See https://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
                      '%(process)d %(thread)d %(message)s'
        },
    },
    'handlers': {
        # 'mail_admins': {
        #     'level': 'ERROR',
        #     'filters': ['require_debug_false', ],
        #     'class': 'django.utils.log.AdminEmailHandler'
        # },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['console', ],
            'level': 'DEBUG',
            'propagate': True
        },
        'django.security.DisallowedHost': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': True
        }
    }
}




# Your production stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------
# Production media in docker volume `media`
MEDIA_ROOT = '/media'


# Sushibar specific settings
# ------------------------------------------------------------------------------
DEFAULT_STUDIO_SERVER = get_env('DEFAULT_STUDIO_SERVER', 'https://studio.learningequality.org')


# Celery settings
# ------------------------------------------------------------------------------
BROKER_URL = "redis://:{hostname}:/{db}".format(
    hostname='os.getenv("CELERY_BROKER_ENDPOINT")',
    db=os.getenv("CELERY_REDIS_DB")
) or BROKER_URL
CELERY_RESULT_BACKEND = "redis://:{hostname}:/{db}".format(
    hostname=os.getenv("CELERY_RESULT_BACKEND_ENDPOINT"),
    db=os.getenv("CELERY_REDIS_DB")
) or CELERY_RESULT_BACKEND
CELERY_TIMEZONE = os.getenv("CELERY_TIMEZONE") or CELERY_TIMEZONE

