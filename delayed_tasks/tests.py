# coding=utf-8
"""delayed_tasks tests"""
import datetime
from unittest import mock

import celery
from django.utils import timezone


from common.tools_test import DTestCaseBase
from delayed_tasks.models import Task
from delayed_tasks.tasks import DelayedRequest, schedule_persisted_tasks


app = celery.Celery('testapp')


@app.task(name='a_test_task')
def a_test_task(*args, **kwargs):
    """A dummy task for testing purposes"""
    pass


class DummyMessage:
    @property
    def body(self):
        """Body"""
        pass

    @property
    def content_type(self):
        """Content_type"""
        pass

    @property
    def properties(self):
        """Properties"""
        pass

    @property
    def delivery_info(self):
        """Delivery_info"""
        pass

    @property
    def content_encoding(self):
        """Content_encoding"""
        pass

    @property
    def payload(self):
        """Payload"""
        return ['hello'], {'test': True}, 'c'


class DelayedTasksTestCase(DTestCaseBase):
    @mock.patch('celery.Celery.control')
    def test_request_init(self, mock_control):
        """Test request init"""
        # -----
        # ETA less than 1 hour from now
        eta = timezone.now() + datetime.timedelta(minutes=30)
        kwargs = {
            'headers': {
                'eta': eta.isoformat(),
                'expires': None,
                'id': 'takis',
                'task': 'a_test_task'
            },
            'app': app
        }
        DelayedRequest(DummyMessage(), **kwargs)
        t = Task.objects.first()
        self.assertIsNone(t)

        # -----
        # ETA more than 1 hour from now
        eta = timezone.now() + datetime.timedelta(hours=2)
        kwargs = {
            'headers': {
                'eta': eta.isoformat(),
                'expires': None,
                'id': 'takis',
                'task': 'a_test_task'
            },
            'app': app
        }
        DelayedRequest(DummyMessage(), **kwargs)
        t = Task.objects.first()
        self.assertEqual(t.eta, eta)
        sig = t.signature
        self.assertEqual(sig['args'], ['hello'])
        self.assertEqual(sig['kwargs'], {'test': True})
        self.assertEqual(sig['options'], {'eta': eta.isoformat()})
        self.assertEqual(sig['immutable'], True)
        self.assertEqual(sig['subtask_type'], None)

    def test_schedule_persisted_tasks(self):
        """Test for schedule_persisted_tasks"""
        now = timezone.now()
        t = Task(
            signature=a_test_task.si(2, test=1),
            eta=now + datetime.timedelta(minutes=9)
        )
        t.save()

        with mock.patch('celery.Celery.tasks') as mock_dict:
            schedule_persisted_tasks()
            mock_dict['a_test_task'].apply_async.assert_called_with([2], {'test': 1})

        # Should delete task
        self.assertEqual(Task.objects.count(), 0)

        t = Task(
            signature=a_test_task.si(2, test=1),
            eta=now + datetime.timedelta(minutes=12)  # ETA after now
        )
        t.save()

        # should not call task
        with mock.patch('celery.Celery.tasks') as mock_dict:
            schedule_persisted_tasks()
            mock_dict['a_test_task'].apply_async.assert_not_called()

        # Should not delete task
        self.assertEqual(list(Task.objects.values_list('id', flat=True)), [t.id])
