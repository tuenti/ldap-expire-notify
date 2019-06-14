# -*- coding: utf-8 -*-
import time
import datetime
import unittest
import threading
import requests_mock

from ldap_expire_notify.channel import webhook

requests_mock.Mocker.TEST_PREFIX = 'test_worker'


def mock_request_matcher(request):
    return 'uid=vcabezas,ou=people,o=test' in request.text and \
            request.path_url == '/vcabezas'


@requests_mock.Mocker()
class TestWebhookChannel(unittest.TestCase):
    def setUp(self):
        self.c = webhook.WebhookChannel('test', {
            'threshold': 10,
            'workers': 1,
            'throttle_code': 444,
            'throttle_retries': 3,
            'url': 'http://test.com/{{ ldap.uid | first }}',
            'method': 'post',
            'body': '{{ dn }}',
            'headers': {
                'Content-Type': 'application/json',
            },
        })

    def tearDown(self):
        self.c.stop()

    def test_init_ko(self):
        with self.assertRaisesRegex(ValueError, '^Required field \w+ is missing'):
            c = webhook.WebhookChannel('webhook-test', {
                'threshold': 1,
                'workers': 1,
            })

        with self.assertRaisesRegex(ValueError, '^throttle_retries must be greater than 0, got -10'):
            c = webhook.WebhookChannel('webhook-test', {
                'threshold': 1,
                'throttle_retries': -10,
                'url': 'http://test.com/{{ ldap.uid | first }}',
            })

        with self.assertRaisesRegex(ValueError, '^throttle_max_sleep must be greater than 0, got -10'):
            c = webhook.WebhookChannel('webhook-test', {
                'threshold': 1,
                'throttle_max_sleep': -10,
                'url': 'http://test.com/{{ ldap.uid | first }}',
            })

    def test_init_ok(self):
        self.assertIsNotNone(self.c.url)
        self.assertEqual(self.c.method, 'POST')
        self.assertEqual(self.c.throttle_code, 444)
        self.assertEqual(self.c.throttle_retries, 3)
        self.assertIsNotNone(self.c.body_tmpl)
        self.assertIn('Content-Type', self.c.headers)
        self.assertEqual(self.c.headers['Content-Type'], 'application/json')

    def test_start(self):
        self.c.start()
        for w in self.c.workers:
            self.assertIsInstance(w, webhook.WebhookWorker)
            self.assertEqual(w.channel, self.c)
            self.assertEqual(w.channel.throttle_code, self.c.throttle_code)
            self.assertEqual(w.channel.throttle_retries, self.c.throttle_retries)

    def test_worker_notify(self, req_mock):
        req_mock.post(
            'http://test.com/vcabezas',
            text='OK',
            additional_matcher=mock_request_matcher,
        )
        self.c.start()
        w = self.c.workers[0]
        w.notify({
            'dn': 'uid=vcabezas,ou=people,o=test',
            'expiration': datetime.datetime.now(),
            'ldap': {
                'uid': ['vcabezas'],
            },
        })

        self.assertEqual(req_mock.call_count, 1)


    def test_worker_notify_throttle(self, req_mock):
        req_mock.post(
            'http://test.com/vcabezas',
            text='OK',
            additional_matcher=mock_request_matcher,
            status_code=444,
            reason='Rate limited',
        )

        self.c.start()
        w = self.c.workers[0]
        was = datetime.datetime.now()
        with self.assertRaises(RuntimeError):
            w.notify({
                'dn': 'uid=vcabezas,ou=people,o=test',
                'expiration': datetime.datetime.now(),
                'ldap': {
                    'uid': ['vcabezas'],
                },
            })
        now = datetime.datetime.now()
        self.assertEqual(req_mock.call_count, w.throttle_retries)
        self.assertGreaterEqual(now - was, datetime.timedelta(seconds=6))

    def test_worker_notify_max_sleep(self, req_mock):
        req_mock.post(
            'http://test.com/vcabezas',
            text='OK',
            additional_matcher=mock_request_matcher,
            status_code=444,
            reason='Rate limited',
        )

        self.c.start()
        w = self.c.workers[0]
        w.throttle_retries = 5
        w.throttle_max_sleep = 1
        was = datetime.datetime.now()
        with self.assertRaises(RuntimeError):
            w.notify({
                'dn': 'uid=vcabezas,ou=people,o=test',
                'expiration': datetime.datetime.now(),
                'ldap': {
                    'uid': ['vcabezas'],
                },
            })
        now = datetime.datetime.now()
        self.assertEqual(req_mock.call_count, w.throttle_retries)
        self.assertGreaterEqual(now - was, datetime.timedelta(seconds=5))
        self.assertLessEqual(now - was, datetime.timedelta(seconds=15))
