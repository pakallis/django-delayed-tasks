# coding=utf-8
"""delayed_tasks apps"""
import celery
from django.apps import AppConfig


class DelayedTasksConfig(AppConfig):
    name = 'delayed_tasks'

    def ready(self):
        """Register receivers from delayed_tasks"""
        from delayed_tasks import receivers  # noqa: F401
        from delayed_tasks import tasks  # noqa: F401
        tasks.setup_periodic_task(celery.current_app)
