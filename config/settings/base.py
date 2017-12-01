"""

Django settings for sushibar project.

"""

import os
from os.path import abspath, dirname, join

# Build sushibar paths starting at the git root like this: join(ROOT_DIR, ...)
ROOT_DIR = dirname(dirname(dirname(abspath(__file__))))
APPS_DIR = join(ROOT_DIR, 'sushibar')
TREES_DIR = join(APPS_DIR, 'trees')

def get_env(var, default=None):
    """
    Looks for `var` in the environment. If env-variable `var` is not found, the
    function returns the `default_value`.
    """
    if var in os.environ:
        return os.environ[var]
    else:
        print('Using default value', str(default), 'for', var)
        return default






# APP CONFIGURATION
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    # Default Django apps:
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Useful template tags:
    # 'django.contrib.humanize',

    # Admin
    'django.contrib.admin',

    'rest_framework',
    'channels',   # remporaryly off
]

THIRD_PARTY_APPS = [
    'crispy_forms',  # Form layouts
]

# Apps specific for this project go here.
LOCAL_APPS = [
    # custom users app
    'sushibar.users.apps.UsersConfig',
    # Your stuff: custom apps go here
    'sushibar.runs',
    'sushibar.dashboard',
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#installed-apps
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# MIDDLEWARE CONFIGURATION
# ------------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]


# DEBUG
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = get_env('DJANGO_DEBUG', False)


# FIXTURE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-FIXTURE_DIRS
FIXTURE_DIRS = (
    join(APPS_DIR, 'fixtures'),
)

# EMAIL CONFIGURATION
# ------------------------------------------------------------------------------
EMAIL_BACKEND = get_env('DJANGO_EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')

# MANAGER CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#admins
ADMINS = [
    ("""LE""", 'ivan@learningequality.org'),
]

# See: https://docs.djangoproject.com/en/dev/ref/settings/#managers
MANAGERS = ADMINS

# DATABASE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': get_env('POSTGRES_DB', 'sushibar'),
        'HOST': 'localhost',
        'USER': get_env('POSTGRES_USER', ''),
        'PASSWORD': get_env('POSTGRES_PASSWORD', ''),
        'PORT': '5432',
    }
}


# GENERAL CONFIGURATION
# ------------------------------------------------------------------------------
# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'UTC'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#language-code
LANGUAGE_CODE = 'en-us'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#site-id
SITE_ID = 1
MIGRATION_MODULES = {
    'sites': 'sushibar.contrib.sites.migrations'
}

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-i18n
USE_I18N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-l10n
USE_L10N = True

# See: https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = True

# TEMPLATE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#templates
TEMPLATES = [
    {
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#std:setting-TEMPLATES-BACKEND
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-dirs
        'DIRS': [
            join(APPS_DIR, 'templates'),
        ],
        'OPTIONS': {
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-debug
            'debug': DEBUG,
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-loaders
            # https://docs.djangoproject.com/en/dev/ref/templates/api/#loader-types
            'loaders': [
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            # See: https://docs.djangoproject.com/en/dev/ref/settings/#template-context-processors
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                # Your stuff: custom template context processors go here
            ],
        },
    },
]

# See: http://django-crispy-forms.readthedocs.io/en/latest/install.html#template-packs
CRISPY_TEMPLATE_PACK = 'bootstrap4'

# STATIC FILE CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-root
STATIC_ROOT = join(ROOT_DIR, 'sushibarstatic')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#static-url
STATIC_URL = '/static/'

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#std:setting-STATICFILES_DIRS
STATICFILES_DIRS = [
    join(APPS_DIR, 'static'),
]

# See: https://docs.djangoproject.com/en/dev/ref/contrib/staticfiles/#staticfiles-finders
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

# MEDIA CONFIGURATION
# ------------------------------------------------------------------------------
# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-root
MEDIA_ROOT = join(ROOT_DIR, 'media')

# See: https://docs.djangoproject.com/en/dev/ref/settings/#media-url
MEDIA_URL = '/media/'

# URL Configuration
# ------------------------------------------------------------------------------
ROOT_URLCONF = 'config.urls'

# See: https://docs.djangoproject.com/en/dev/ref/settings/#wsgi-application
WSGI_APPLICATION = 'config.wsgi.application'

# PASSWORD STORAGE SETTINGS
# ------------------------------------------------------------------------------
# See https://docs.djangoproject.com/en/dev/topics/auth/passwords/#using-argon2-with-django
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.BCryptPasswordHasher',
]

# PASSWORD VALIDATION
# https://docs.djangoproject.com/en/dev/ref/settings/#auth-password-validators
# ------------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# AUTHENTICATION CONFIGURATION
# ------------------------------------------------------------------------------
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'sushibar.ccserverlib.auth_backend.ContentCurationServerAuthBackend',
]


# Custom user app defaults
# Select the correct user model
AUTH_USER_MODEL = 'users.BarUser'
LOGIN_REDIRECT_URL = 'users:redirect'
LOGIN_URL = 'sushibar_signin'

# SLUGLIFIER
AUTOSLUG_SLUGIFY_FUNCTION = 'slugify.slugify'


# Location of root django.contrib.admin URL, use {% url 'admin:index' %}
ADMIN_URL = r'^admin/'

# Your common stuff: Below this line define 3rd party library settings
# ------------------------------------------------------------------------------

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "asgi_redis.RedisChannelLayer",
        "CONFIG": {
            "hosts": [get_env('REDIS_URL', 'redis://localhost:6379')],
        },
        "ROUTING": "sushibar.runs.routing.channel_routing",
    },
}


# Settings for storing progress in redis  (used for sushichef MMVP)
MMVP_REDIS_HOST = 'redis'
MMVP_REDIS_PORT = 6379
MMVP_REDIS_DB = 0
MMVP_REDIS_TEST_DB = 1



# Sushibar specific settings
# ------------------------------------------------------------------------------

DEFAULT_STUDIO_SERVER = get_env('DEFAULT_STUDIO_SERVER', 'https://develop.contentworkshop.learningequality.org')




# Trello integraion
# ------------------------------------------------------------------------------
TRELLO_API_KEY = get_env('TRELLO_API_KEY')
TRELLO_TOKEN = get_env('TRELLO_TOKEN')
TRELLO_BOARD = get_env('TRELLO_BOARD')


# Google integraion
# ------------------------------------------------------------------------------
GOOGLE_AUTH_JSON = "credentials/client_secret.json"
GOOGLE_QA_TEMPLATE_ID = get_env('GOOGLE_QA_TEMPLATE_ID', default='11Wxms1ZcAI_stQ1L0w1G2vC9shPDf67u1VIERnz93YM')
TARGET_FOLDER_ID = get_env('TARGET_FOLDER_ID', default="1dwZwAjRTkPYeOipdYSsCsLj2l1CjDYg2")
LOCAL_DEV_DEFAULT_DOMAIN = None   # set to something like `92832de0.ngrok.io` for testing webhooks

