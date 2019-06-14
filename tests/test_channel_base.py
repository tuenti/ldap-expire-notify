# -*- coding: utf-8 -*-
import time
import datetime
import unittest
import threading
import logging

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

from ldap_expire_notify.channel import base


class TestChannelWorkerCls(base.ChannelWorker):
    def __init__(self, *args, **kwargs):
        super(TestChannelWorkerCls, self).__init__(*args, **kwargs)


class TestChannelCls(base.Channel):
    def new_worker(self):
        return TestChannelWorkerCls(self, self.queue)


class TestChannel(unittest.TestCase):
    def setUp(self):
        self.c = TestChannelCls('test', {
            'threshold': 10,
            'workers': 1,
        })
        self.buf = StringIO()
        self.handler = logging.StreamHandler(self.buf)
        logging.getLogger('ldap-expire-notify').addHandler(self.handler)

    def tearDown(self):
        self.c.stop()
        logging.getLogger('ldap-expire-notify').removeHandler(self.handler)

    def test_init(self):
        self.assertEqual(self.c.name, 'test')
        self.assertEqual(self.c.threshold, 10)

    def test_check_and_notify(self):
        expiration = datetime.datetime.now() + datetime.timedelta(seconds=self.c.threshold + 1)
        self.assertFalse(self.c.check_and_notify(expiration, 'uid=test', {'trigger': False}))

        # Ensure that check is triggered
        expiration = datetime.datetime.now() - datetime.timedelta(seconds=self.c.threshold + 1)
        self.assertTrue(self.c.check_and_notify(expiration, 'uid=test', {'trigger': True}))
        task = self.c.queue.get(timeout=1)
        self.assertEqual(task['expiration'], expiration)
        self.assertEqual(task['dn'], 'uid=test')
        self.assertEqual(task['ldap'], {'trigger': True})

    def test_check_configuration(self):
        with self.assertRaisesRegex(ValueError, '^Required field \w+ is missing'):
            self.c.check_configuration({})

    def test_start_stop(self):
        self.c.start()
        self.assertEqual(len(self.c.workers), 1)
        for w in self.c.workers:
            self.assertIsInstance(w, TestChannelWorkerCls)

        self.c.stop()
        self.assertEqual(len(self.c.workers), 0)

    def test_worker_run(self):
        self.c.start()
        self.c.queue.put(False)

        self.c.queue.join()
        self.assertRegex(self.buf.getvalue(), r'\bUnable to notify task False\b')
