import django
import pytest

pytest_plugins = ('celery.contrib.pytest',)


@pytest.fixture(scope='session')
def celery_config():
    return {
        'broker_connection_timeout': 10000,
        'worker_lost_wait': 100000,
        'redis_socket_timeout': 100000,
        'result_backend_transport_options': {'visibility_timeout': 18000},
        'broker_url': 'amqp://guest:guest@rabbitmq:5672',
        'result_backend': 'redis://redis:6379'
    }


def pytest_configure(config):
    from django.conf import settings

    # USE_L10N is deprecated, and will be removed in Django 5.0.
    use_l10n = {"USE_L10N": True} if django.VERSION < (4, 0) else {}
    settings.configure(
        CACHES={
            'default': {
                'BACKEND': 'django.core.cache.backends.redis.RedisCache',
                'LOCATION': 'redis://redis:6379'
            }
        },
        DATABASES={
            'default': {
                'ENGINE': 'django.db.backends.postgresql_psycopg2',
                'NAME': 'test',
                'USER': 'test',
                'PASSWORD': 'test',
                'HOST': 'postgresql',
                'PORT': 5432
            }
        },
        USE_TZ=True,
        SITE_ID=1,
        SECRET_KEY='not very secret in tests',
        USE_I18N=True,
        INSTALLED_APPS=(
            'delayed_tasks',
        ),
        **use_l10n,
    )

    django.setup()
