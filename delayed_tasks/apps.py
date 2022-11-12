# coding=utf-8
"""delayed_tasks apps"""
import celery
from django.apps import AppConfig


class DelayedTasksConfig(AppConfig):
    name = 'delayed_tasks'
    default_auto_field = 'django.db.models.AutoField'
    verbose_name = 'Delayed Tasks'

    def ready(self):
        # Register all hooks and setup periodic task
        from delayed_tasks import receivers  # noqa: F401
        from delayed_tasks import tasks  # noqa: F401
        tasks.setup_periodic_task(celery.current_app)
