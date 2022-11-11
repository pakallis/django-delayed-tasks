# coding=utf-8
"""delayed_tasks models"""

from django.db import models


class Task(models.Model):
    signature = models.JSONField()
    eta = models.DateTimeField(db_index=True)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
