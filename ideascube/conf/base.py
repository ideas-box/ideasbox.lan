# -*- coding: utf-8 -*-
"""Django settings for ideascube project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

import os

from django.conf.locale import LANG_INFO
from django.utils.translation import ugettext_lazy as _

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
PROJECT_DIR = os.path.join(BASE_DIR, 'ideascube')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.7/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '16exrv_@=2(za=oj$tj+l_^v#sbt83!=t#wz$s+1udfa04#vz!'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(os.environ.get('DEBUG', True))

ALLOWED_HOSTS = ['.ideascube.lan', 'localhost']


# Application definition

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'ideascube',
    'ideascube.configuration',
    'ideascube.serveradmin',
    'ideascube.blog',
    'ideascube.library',
    'ideascube.search',
    'ideascube.mediacenter',
    'ideascube.monitoring',
    'taggit',
    'django_countries',
)

MIDDLEWARE = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'APP_DIRS': True,
        'DIRS': (
            os.path.join(PROJECT_DIR, 'templates'),
        ),
        'OPTIONS': {
            'context_processors': (
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.debug",
                "django.template.context_processors.i18n",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "ideascube.context_processors.server",
                "ideascube.context_processors.settings",
                "ideascube.context_processors.version",
            )
        }
    },
]


ROOT_URLCONF = 'ideascube.urls'

WSGI_APPLICATION = 'ideascube.wsgi.application'

LOGIN_REDIRECT_URL = 'index'
LOGIN_URL = 'login'

# Internationalization
# https://docs.djangoproject.com/en/1.7/topics/i18n/

LANGUAGE_CODE = 'en'

TIME_ZONE = os.environ.get('TIME_ZONE', 'UTC')

USE_I18N = True

USE_L10N = True

USE_TZ = True

# Add languages we're missing from Django
LANG_INFO.update({
    'am': {
        'bidi': False,
        'name': 'Amharic',
        'code': 'am',
        'name_local': u'አማርኛ'
    },
    'bm': {
        'bidi': False,
        'name': 'Bambara',
        'code': 'bm',
        'name_local': 'Bambara'
    },
    'ckb': {
        'bidi': True,
        'name': 'Soranî',
        'code': 'ckb',
        'name_local': 'سۆرانی',
    },
    'ku': {
        'bidi': False,
        'name': 'Kurdish',
        'code': 'ku',
        'name_local': 'Kurdî'
    },
    'ln': {
        'bidi': False,
        'name': 'Lingala',
        'code': 'ln',
        'name_local': 'Lingála'
    },
    'ps': {
        'bidi': True,
        'name': 'Pashto',
        'code': 'ps',
        'name_local': 'پښتو'
    },
    'rn': {
        'bidi': False,
        'name': 'Kirundi',
        'code': 'rn',
        'name_local': 'kirundi'
    },
    'so': {
        'bidi': False,
        'name': 'Somali',
        'code': 'so',
        'name_local': u'Af-Soomaali'
    },
    'ti': {
        'bidi': False,
        'name': 'Tigrinya',
        'code': 'bm',
        'name_local': 'ትግርኛ'
    },
    'wo': {
        'bidi': False,
        'name': 'Wolof',
        'code': 'wo',
        'name_local': 'wolof'
    },
})

# Languages that will be available as UI translations
_AVAILABLE_LANGUAGES = (
    'am',
    'ar',
    'bm',
    'en',
    'es',
    'fr',
    'so',
    'sw',
)
LANGUAGES = []
for code, lang_data in sorted(LANG_INFO.items()):
    if code in _AVAILABLE_LANGUAGES:
        LANGUAGES.append((code, lang_data['name_local'].capitalize()))

LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'ideascube', 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.7/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATICFILES_DIRS = [
    '/usr/share/ideascube/static',
    ]
MEDIA_URL = '/media/'


# Ideas Box specifics
STORAGE_ROOT = os.environ.get('STORAGE_ROOT',
                              os.path.join(BASE_DIR, 'storage'))

# Loaded relatively to STORAGE_ROOT on settings.py
BACKUPED_ROOT = None
MEDIA_ROOT = None
STATIC_ROOT = None
DATABASES = None

AUTH_USER_MODEL = 'ideascube.User'
IDEASCUBE_PLACE_NAME = _('the camp')

LOAN_DURATION = 0  # In days.

DOMAIN = 'ideascube.lan'

# Fields to be used in the entry export. This export is supposed to be
# anonymized, so no personal data like name.
MONITORING_ENTRY_EXPORT_FIELDS = ['birth_year', 'gender']

USERS_LIST_EXTRA_FIELDS = ['serial']

USER_INDEX_FIELDS = ['short_name', 'full_name', 'serial']

USER_FORM_FIELDS = (
    (_('Basic informations'), ['serial', 'short_name', 'full_name']),
)

ENTRY_ACTIVITY_CHOICES = [
]

STAFF_HOME_CARDS = [
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'user_list',
        'title': _('Users'),
        'description': _('Create, remove or modify users.'),
        'fa': 'users',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'monitoring:entry',
        'title': _('Entries'),
        'description': _('Manage user entries.'),
        'fa': 'sign-in',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'monitoring:stock',
        'title': _('Stock'),
        'description': _('Manage stock.'),
        'fa': 'barcode',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'monitoring:loan',
        'title': _('Loans'),
        'description': _('Manage loans.'),
        'fa': 'exchange',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'server:power',
        'title': _('Stop/Restart'),
        'description': _('Stop or restart the server.'),
        'fa': 'power-off',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'server:wifi',
        'title': _('Wi-Fi'),
        'description': _('Manage Wi-Fi connections.'),
        'fa': 'wifi',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'server:name',
        'title': _('Server Name'),
        'description': _('Change the server name.'),
        'fa': 'info-circle',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'server:home_page',
        'title': _('Home page'),
        'description': _('Manage home page'),
        'fa': 'th',
    },
    {
        'is_staff': True,
        'category': 'manage',
        'url': 'server:languages',
        'title': _('Languages'),
        'description': _('Enable or disable languages.'),
        'fa': 'language',
    },
]

HOME_CARDS = [
    {
        'id': 'blog',
    },
    {
        'id': 'library',
    },
    {
        'id': 'mediacenter',
    },
    # {
    #     'category': 'learn',
    #     'url': 'http://mydomain.fr',
    #     'title': 'The title of my custom card',
    #     'description': 'The description of my custom card',
    #     'img': '/img/wikipedia.png',
    #     'fa': 'fax',
    # },
]

# Database
# https://docs.djangoproject.com/en/1.7/ref/settings/#databases

SERVICES = [
    {'name': 'uwsgi', 'description': _('Python web server')},
    {'name': 'nginx', 'description': _('Global proxy')},
    {
        'name': 'kalite',
        'description': _('Daemon which provides KhanAcademy on lan'),
    },
    {'name': 'wikipedia',
        'description': _('Daemon which provides Wikipedia on lan')},
    {'name': 'gutenberg',
        'description': _('Daemon which provides Gutenberg on lan')},
    {'name': 'ssh',
        'description': _('Daemon used for distant connexion to server')},
]


SESSION_COOKIE_AGE = 60 * 60  # Members must be logged out after one hour
SESSION_SAVE_EVERY_REQUEST = True
BACKUP_FORMAT = 'gztar'  # One of 'tar', 'bztar', 'gztar'
TAGGIT_CASE_INSENSITIVE = True
TAGGIT_TAGS_FROM_STRING = 'ideascube.utils.tag_splitter'
DATABASE_ROUTERS = ['ideascube.db_router.DatabaseRouter']
