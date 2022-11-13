import datetime
import time

from django.core.cache import cache
from django.test import override_settings
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, TaskRevokedError
from django.utils import timezone
import pytest

from delayed_tasks.models import Task
from delayed_tasks.tasks import DelayedTask, schedule_persisted_tasks


@shared_task(bind=True, base=DelayedTask)
def retry_task(self, key, seconds, max_retries):
    cache.incr(key)
    eta = timezone.now() + datetime.timedelta(seconds=seconds)
    self.retry(eta=eta, max_retries=max_retries)


@shared_task(bind=True, base=DelayedTask)
def simple_task(self, key):
    cache.incr(key)

def cleanup(app):
    Task.objects.all().delete()
    # remove pending tasks
    app.control.purge()

    # remove active tasks
    i = app.control.inspect()
    jobs = i.active()
    for hostname in jobs:
        tasks = jobs[hostname]
        for task in tasks:
            app.control.revoke(task['request']['id'], terminate=True)

    # remove reserved tasks
    jobs = i.reserved()
    for hostname in jobs:
        tasks = jobs[hostname]
        for task in tasks:
            app.control.revoke(task['request']['id'], terminate=True)

    # remove scheduled tasks
    jobs = i.scheduled()
    for hostname in jobs:
        tasks = jobs[hostname]
        for task in tasks:
            app.control.revoke(task['request']['id'], terminate=True)

    count = 0
    while len(list(i.scheduled().values())[0]) > 0:
        if count > 10:
            raise Exception('Could not cleanup')
        count += 1


def test_simple_task(celery_app, celery_worker):
    cleanup(celery_app)
    # --------------------------
    # simple_task without eta
    key = 'simple_task'
    cache.set(key, 0)
    with override_settings(DELAYED_TASKS_STORE_TASK_ETA_MINUTES=0):
        res = simple_task.s(key).apply_async()
        res.wait(timeout=10)
    assert res.status == 'SUCCESS'
    assert cache.get(key) == 1
    assert Task.objects.count() == 0

    # --------------------------
    # simple_task with eta
    key = 'simple_task_eta'
    cache.set(key, 0)
    task_eta_seconds = 4
    now = timezone.now()
    eta = now + datetime.timedelta(seconds=task_eta_seconds)
    with override_settings(DELAYED_TASKS_STORE_TASK_ETA_MINUTES=0):
        res = simple_task.s(key).apply_async(eta=eta)
        with pytest.raises(TaskRevokedError):
            res.wait(timeout=10)
    # Should appear as revoked because we revoked the current and re-schedule another task
    assert res.status == 'REVOKED'
    assert cache.get(key) == 0
    assert Task.objects.count() == 1

    with override_settings(DELAYED_TASKS_SCHEDULE_TASK_AHEAD_ETA_MINUTES=0):
        schedule_persisted_tasks()

    # Task not scheduled yet
    assert Task.objects.count() == 1
    assert cache.get(key) == 0

    with override_settings(DELAYED_TASKS_SCHEDULE_TASK_AHEAD_ETA_MINUTES=10):
        schedule_persisted_tasks()

    # Task should be scheduled and removed from db
    assert Task.objects.count() == 0
    i = celery_app.control.inspect()
    scheduled_task = list(i.scheduled().values())[0][0]
    assert scheduled_task['eta'] == eta.isoformat()
    assert scheduled_task['request']['name'] == 'tests.test_delayed_tasks.simple_task'
    assert scheduled_task['request']['args'] == ['simple_task_eta']


    # Wait some time for ETA to expire and task to be executed
    time.sleep(task_eta_seconds + 1)
    # Should have increased counter as task is now executed
    assert cache.get(key) == 1

    # --------------------------
    # retry_task
    key = 'retry_task'
    cache.set(key, 0)
    retry_in_seconds = 4
    max_retries = 4
    with override_settings(DELAYED_TASKS_STORE_TASK_ETA_MINUTES=0):
        res = retry_task.s(key, retry_in_seconds, max_retries).apply_async(
            eta=timezone.now() + datetime.timedelta(seconds=0.2)
        )
        with pytest.raises(TaskRevokedError):
            res.wait(timeout=10)

    # Task should be in the database and not scheduled
    assert Task.objects.count() == 1
    i = celery_app.control.inspect()
    scheduled_tasks = list(i.scheduled().values())[0]
    assert not scheduled_tasks

    with override_settings(DELAYED_TASKS_SCHEDULE_TASK_AHEAD_ETA_MINUTES=10):
        schedule_persisted_tasks()
    # Task should be scheduled to run on eta and not exist on DB
    assert Task.objects.count() == 0
    scheduled_task = list(i.scheduled().values())[0][0]
    assert scheduled_task['eta'] <= (timezone.now() + datetime.timedelta(seconds=retry_in_seconds)).isoformat()
    assert cache.get(key) == 1
    # Wait for task to run and be retried
    time.sleep(retry_in_seconds + 0.5)
    assert cache.get(key) == 2
    assert Task.objects.count() == 0
    time.sleep(retry_in_seconds + 0.5)
    assert cache.get(key) == 3
    assert Task.objects.count() == 0

    cleanup(celery_app)

    # --------------------------
    # Max retries exceeded
    max_retries = 2
    retry_in_seconds = 1
    key = 'retry_task_max_retries'
    cache.set(key, 0)
    with override_settings(DELAYED_TASKS_STORE_TASK_ETA_MINUTES=0):
        res = retry_task.s(key, retry_in_seconds, max_retries).apply_async(
            eta=timezone.now() + datetime.timedelta(seconds=0.2)
        )
        with pytest.raises(TaskRevokedError):
            res.wait(timeout=10)

    with override_settings(DELAYED_TASKS_SCHEDULE_TASK_AHEAD_ETA_MINUTES=10):
        schedule_persisted_tasks()

    # Wait for all retries
    time.sleep(3 * retry_in_seconds + 0.5)
    # TODO: Should be 2
    assert cache.get(key) == 3
