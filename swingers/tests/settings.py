import os


# are we postgis enabled?
if os.environ.get('POSTGIS'):
    DATABASES = {
        'default': {
            'NAME': 'swingers_test',
            'USER': 'postgres',
            'ENGINE': 'django.contrib.gis.db.backends.postgis',
        },
    }
    GIS_ENABLED = True
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3'
        }
    }
    GIS_ENABLED = False


SITE_NAME = 'test'
SITE_ID = 1
SERVICE_NAME = 'swingers'

ROOT_URLCONF = 'urls'

USE_TZ = True

MIDDLEWARE_CLASSES = (
    'swingers.middleware.html.HtmlMinifyMiddleware',
    'swingers.middleware.html.JsCssCompressMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'swingers.middleware.transaction.TransactionMiddleware',
    'swingers.middleware.auth.AuthenticationMiddleware',
)

ALLOW_ANONYMOUS_ACCESS = False
ANONYMOUS_USER_ID = -1

STATICFILES_FINDERS = (
    'compressor.finders.CompressorFinder',
)


INSTALLED_APPS = (
    'swingers',
    'swingers.sauth',
    'swingers.tests',   # the test fixtures are loaded from here

    'reversion',
    'compressor',

    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.redirects',
    'django.contrib.messages',
    'django.contrib.gis',
)

SECRET_KEY = 'test'

STATIC_URL = '/static/'

HTML_MINIFY = True

COMPRESS_ENABLED = True
COMPRESS_JS_COMPRESSOR = 'swingers.compress.JsCssCompressor'
COMPRESS_PARSER = 'swingers.compress.CompressParser'
