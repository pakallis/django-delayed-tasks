import datetime
import time

from django.core.cache import cache
from celery import shared_task
from django.utils import timezone
from delayed_tasks.tasks import DelayedTask, schedule_persisted_tasks


import uuid

key = str(uuid.uuid4())

cache.set(key, 0)


@shared_task(bind=True, base=DelayedTask)
def a_test_task(self):
    cache.incr(key)
    self.retry(
        eta=timezone.now() + datetime.timedelta(seconds=0.1), max_retries=4
    )


def test_a(celery_app, celery_worker):
    a_test_task.s().apply_async()
    time.sleep(1)
    schedule_persisted_tasks()
    time.sleep(1)
    schedule_persisted_tasks()
    time.sleep(1)
    assert cache.get(key) == 5
