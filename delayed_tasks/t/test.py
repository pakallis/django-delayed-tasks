import datetime

from celery.exceptions import MaxRetriesExceededError
from django.utils import timezone
import pytest

from celery import shared_task

@shared_task(bind=True)
def a_test_task(self):
    self.retry(countdown=100, max_retries=3)


def test_a(celery_app, celery_worker):
    a_test_task.s().set(retries=2).apply_async()
