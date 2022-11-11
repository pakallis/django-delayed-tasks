# coding=utf-8
"""delayed_tasks tasks"""

import datetime
import logging

import celery
import celery.exceptions
from celery.utils.time import maybe_iso8601, maybe_make_aware
from celery.worker.request import Request
from django.utils import timezone

from delayed_tasks.models import Task
from delayed_tasks.settings import app_settings


logger = logging.getLogger(__name__)


class DelayedRequest(Request):
    def __init__(self, *args, **kwargs):
        """Init delayed request

        Override Request object to re-schedule tasks that have eta > now + STORE_TASK_ETA_MINUTES.
        The re-scheduled tasks are discarded from the celery worker and are persisted in the database so that they
        can be picked and re-scheduled later by `run_persisted_tasks`.
        """
        logger.info('DelayedRequest#init: %s', kwargs)
        expires_set = False
        try:
            # Required to be set before calling _maybe_set_expires_based_on_eta
            self._app = kwargs['app']
            expires_set = self._maybe_set_expires(kwargs)
        except Exception as e:
            # If an exception occurs, log the message and use the existing implementation as we don't to skip running
            # the task
            logger.exception(e)

        super().__init__(*args, **kwargs)

        try:
            self._maybe_save_task(expires_set)
        except Exception as e:
            logger.exception(e)

    def _maybe_save_task(self, expires_set) -> None:
        """Save a task

        Save the task in the database if eta > now + STORE_TASK_ETA_MINUTES so that it can be re-scheduled later
        by the task `run_persisted_tasks`
        """
        # If task has no eta, then no need to persist it in the database, it will be executed instantly in the worker

        if not expires_set:
            return

        eta = self.eta

        sig = self.task.si(*self.args, **self.kwargs).set(eta=eta.isoformat())

        t = Task(
            signature=sig,
            eta=eta
        )
        t.save()
        logger.info('Task saved to db id: %s, db_id: %s - name: %s - eta: %s', self.task_id, t.id, self.task_name, eta)

    def _eta_from_kwargs(self, kwargs) -> datetime.datetime:
        """Retrieve the eta as datetime from kwargs"""
        eta_str = kwargs['headers']['eta']
        eta = None
        if eta_str is not None:
            try:
                eta = maybe_iso8601(eta_str)
            except (AttributeError, ValueError, TypeError) as exc:
                raise celery.exceptions.InvalidTaskError(f'invalid ETA value {eta_str!r}: {exc}')
            eta = maybe_make_aware(eta, self.tzlocal)
        return eta

    def _maybe_set_expires(self, kwargs) -> bool:
        """Set expires based kwargs. Returns a boolean if the `expires` field was set or not

        Set the 'expires' header based on kwargs. This is kind of a hacky solution to force the Celery worker
        not to schedule this task.

        If the task has eta that is > now + STORE_TASK_ETA_MINUTES then we set the 'expires' header to a past value.
        Setting the 'expires' header to a past value will instantly discard the task and not schedule it in the worker.

        In this step, we don't want to schedule this task in the worker but save it in the database, so that it can be
        picked and re-scheduled by `schedule_persisted_tasks` task.

        By discarding the task in the Celery worker and saving it to the database, we save a large amount of memory in
        RabbitMQ and the Celery worker, as
        1. RabbitMQ does not reserve memory for having an unacknowledged message in the queue
        2. The worker does not reserve memory for having a scheduled task in its memory
        """
        now = timezone.now()

        if kwargs['headers']['expires'] is not None:
            return False

        eta = self._eta_from_kwargs(kwargs)

        if eta is None:
            return False

        if eta < now + datetime.timedelta(minutes=int(app_settings.STORE_TASK_ETA_MINUTES)):
            return False

        kwargs['headers']['expires'] = timezone.now() - datetime.timedelta(seconds=100)
        logger.info('Expires set: %s', kwargs['headers']['id'])
        return True


class DelayedTask(celery.Task):
    Request = DelayedRequest


@celery.current_app.task(name='delayed_tasks.tasks.schedule_persisted_tasks')
def schedule_persisted_tasks():
    """Re-schedule persisted tasks

    Fetch tasks that have an ETA about to be executed soon (less than SCHEDULE_TASK_AHEAD_MINUTES from now)
    and schedule them to run exactly on eta, indicated by task['signature']['options']['eta'].
    The scheduled tasks will be added to the RabbitMQ queue and will be fetched by a Celery worker that will wait for
    the ETA to expire to run this task. If the task is scheduled successfully, we remove it from the database.
    """
    max_eta = timezone.now() + datetime.timedelta(minutes=int(app_settings.SCHEDULE_TASK_AHEAD_ETA_MINUTES))
    tasks_to_delete = set()
    for task in Task.objects.filter(eta__lte=max_eta).values():
        signature_dict = task['signature']
        sig = celery.signature(signature_dict)
        task_id = task['id']
        try:
            logger.info('Scheduling task: %s', sig.__json__())
            sig.apply_async()
            # Task successfully scheduled, remove it from DB
            tasks_to_delete.add(task_id)
        except celery.exceptions.NotRegistered:
            # If the task is not registered (usually it does not exist anymore), then remove it from the
            # database to avoid running it again and again.
            tasks_to_delete.add(task_id)
        except Exception as e:  # Skip to the next task instead of raising
            logger.exception(e)

    Task.objects.filter(pk__in=tasks_to_delete).delete()


def setup_periodic_task(celery_app, **kwargs):
    """Setup periodic task"""
    logger.info('Adding periodic task: %s - %s', celery_app, schedule_persisted_tasks)
    celery_app.add_periodic_task(
        datetime.timedelta(minutes=int(app_settings.SCHEDULE_TASKS_INTERVAL_MINUTES)),
        schedule_persisted_tasks.s(),
        name='schedule_persisted_tasks'
    )
