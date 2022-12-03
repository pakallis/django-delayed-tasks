import os

DELAYED_TASKS_STORE_TASK_ETA_MINUTES = 60
DELAYED_TASKS_SCHEDULE_TASK_AHEAD_ETA_MINUTES = 10
DELAYED_TASKS_SCHEDULE_TASKS_INTERVAL_MINUTES = 2
TEST_DB_HOST = os.getenv("TEST_DB_HOST")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": "test",
        "USER": "test",
        "PASSWORD": "test",
        "HOST": TEST_DB_HOST,
        "PORT": 5432,
    }
}
SITE_ID = 1
SECRET_KEY = "not very secret in tests"
USE_I18N = True
INSTALLED_APPS = ("delayed_tasks",)
