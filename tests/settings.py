DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'test',
        'USER': 'test',
        'PASSWORD': 'test',
        'HOST': 'postgresql',
        'PORT': 5432
    }
}
SITE_ID = 1
SECRET_KEY = 'not very secret in tests'
USE_I18N = True
INSTALLED_APPS = (
    'delayed_tasks',
)
