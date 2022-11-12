# coding=utf-8
"""delayed_tasks settings"""
import logging

from django.conf import settings
from django.core.signals import setting_changed


DATABASES={
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}
SITE_ID=1
SECRET_KEY='not very secret in tests'
USE_I18N=True

DEFAULTS = {
    'STORE_TASK_ETA_MINUTES': 0,
    'SCHEDULE_TASK_AHEAD_ETA_MINUTES': 10,
    'SCHEDULE_TASKS_INTERVAL_MINUTES': 2
}

logger = logging.getLogger()


class Settings:
    def __init__(self, user_settings=None, defaults=None):
        """A settings object to store settings for delayed_tasks"""
        if user_settings:
            self._user_settings = user_settings

        self.defaults = defaults or DEFAULTS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        """Keeps user settings"""
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'DELAYED_TASKS', {})
        return self._user_settings

    def __getattr__(self, attr):
        """Override __getattr__ to have a convenient way to access settings"""
        if attr not in self.defaults:
            raise AttributeError(f"Invalid setting: '{attr}' ")
        try:
            val = self.user_settings[attr]
        except KeyError:
            val = self.defaults[attr]

        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        """Reload app settings"""
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


app_settings = Settings(None, defaults=DEFAULTS)


def reload_settings(*args, **kwargs):
    """Reload app settings"""
    setting = kwargs['setting']
    if 'DELAYED_TASKS' in setting:
        logger.info('Reloading settings')
        app_settings.reload()


setting_changed.connect(reload_settings)
