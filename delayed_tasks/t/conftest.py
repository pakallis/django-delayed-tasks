import pytest

pytest_plugins = ('celery.contrib.pytest',)

@pytest.fixture(scope='session')
def celery_config():
    return {
            'broker_url': 'amqp://guest:guest@rabbitmq:5672',
            'result_backend': 'cache+memcached://memcached:11211'
    }

