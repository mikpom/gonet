import os
import sys
import json
from django.core.mail.backends.smtp import EmailBackend
from django.core.exceptions import ImproperlyConfigured
from . import pickle_status

TESTING = len(sys.argv) > 1 and sys.argv[1] == 'test'
SHELLENV = len(sys.argv) > 1 and sys.argv[1] == 'shell'
RECALCULATE = True
if not RECALCULATE:
    sts = pickle_status()
    if sts == 'outdated':
        print('W: Ignoring RECALCULATE=False because'\
              +' source tree is newer than pickles.')
        RECALCULATE = True
    elif sts == 'not found':
        print('W: Ignoring RECALCULATE=False because'\
              +' pickle files not found.')
        RECALCULATE = True
    elif sts == 'up-to-date':
        print('W: Using pickles for data structures.')
    else:
        print('W: Unknown pickle status')
else:
    print('W: Recalculating data structures RECALCULATE is True.')

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.isfile(os.path.join(BASE_DIR, 'secrets.json')):
    with open(os.path.join(BASE_DIR, 'secrets.json')) as secrets_file:
        secrets = json.load(secrets_file)
else:
    secrets = {}

def get_secret(setting, secrets=secrets):
    """Get secret setting or fail with ImproperlyConfigured"""
    try:
        return secrets[setting]
    except KeyError:
        if setting=='SECRET_KEY':
            return 'r4_cu!(h7(wk^34l9lxsn96tp*+mktg&9#!ig#hxeasx*!^7b*'
        elif 'EMAIL' in setting:
            return None
        raise ImproperlyConfigured("Set the {} setting".format(setting))
    

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = get_secret('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
ALLOWED_HOSTS = [u'testserver', u'127.0.0.1']
ADMINS = [('ADMIN', get_secret('EMAIL_HOST_USER'))]
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_SSL = True
EMAIL_HOST = get_secret('EMAIL_HOST')
SERVER_EMAIL = get_secret('SERVER_EMAIL')
EMAIL_HOST_USER = get_secret('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = get_secret('EMAIL_HOST_PASSWORD')
EMAIL_PORT = get_secret('EMAIL_PORT')

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gonet.apps.GOnetConfig'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gonet.rooturls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gonet.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases
try:
   DATA_DIR = os.environ['GONET_DATA']
except KeyError:
    # another attempt to get GONET_DATA folder from secrets file
    try:
        DATA_DIR = get_secret('GONET_DATA')
    except ImproperlyConfigured:
        raise ImproperlyConfigured('Please configure GONET_DATA '\
                                   +'environment variable where\n'\
                                   +'app data and logs will be stored.')
   
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(DATA_DIR, 'gonet.sqlite3'),
        'timeout' : 20,
    }
}

MEDIA_ROOT = os.path.join(DATA_DIR, 'uploads')

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/gonet/static/'

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
    os.path.join(BASE_DIR, "assets"),
]

# LOGGING
LOGGING = {
   'version': 1,
   'disable_existing_loggers': False,
   'formatters': {
      'verbose': {
          'format': '%(asctime)s %(module)s T-%(thread)d jobid<%(jobid)s> %(message)s'
      },
      'simple': {
         'format': '%(levelname)s %(message)s'
      },
   }, 
   'handlers': {
      'mainlog': {
         'level': 'DEBUG',
         'class': 'logging.FileHandler',
         'filename':  os.path.join(DATA_DIR,  'gonet.log'),
      },
      'verbose' : {
         'level': 'DEBUG',
         'class': 'logging.FileHandler',
         'filename':  os.path.join(DATA_DIR,  'gonet_verbose.log'),
         'formatter' : 'verbose'
      },
      'console': {
         'level' : 'DEBUG',
         'class': 'logging.StreamHandler',
         'formatter' : 'verbose'
      },
      
      'mail_admins': {
        'level': 'ERROR',
        'class': 'django.utils.log.AdminEmailHandler',
    }

    },
   'loggers': {
      'django': {
         'handlers': ['mainlog', 'mail_admins'],
         'level': 'INFO',
         'propagate': True,
      },
      'gonet' : {
         'handlers': ['verbose', 'console', 'mail_admins'],
         'level': 'DEBUG',
         'propagate': True,
      }
   },
}

CELERY_LOGGING = {
    'version':1,
    'formatters':{
        'brief':{'format':'%(message)s'},
    },
    'handlers':{
        'console':{
            'class':'logging.StreamHandler', 'level':'INFO', 'formatter':'brief'
        },
        'celery_log':{
            'class':'logging.FileHandler',
            'filename':os.path.join(DATA_DIR,  'celery.log'),
            'level':'WARNING', 'formatter':'brief'
        }
    },
    'loggers' : {
        'heatmap.tasks':{
            'level':'DEBUG',
            'handlers':['console', 'celery_log']
        },
        'celery':{
            'level':'DEBUG',
            'handlers':['console', 'celery_log']
        },        
    }
}
