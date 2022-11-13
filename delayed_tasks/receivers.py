# coding=utf-8
"""delayed_tasks receivers"""
import datetime
import logging

from celery.signals import task_received, task_retry
from django.utils import timezone


logger = logging.getLogger(__name__)


@task_received.connect
def log_task_received(*args, **kwargs):
    """Log task params when a task is received"""
    try:
        request = kwargs['request']
        req_dict = request.request_dict
        if request.eta is not None and request.eta < timezone.now() - datetime.timedelta(hours=1):
            logger.error('outdated task: %s - %s - %s', req_dict['eta'], req_dict['id'], req_dict['task'])
    except Exception as e:
        logger.exception(e)


@task_retry.connect
def log_task_retried(*args, **kwargs):
    """Log task params when a task is retried"""
    try:
        request = kwargs['request']
        print('Task retried', request, request.eta)
        if (eta := request.eta) is not None:
            logger.info('Task retried: %s - %s', request, eta)
    except Exception as e:
        logger.exception(e)
