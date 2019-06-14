# -*- coding: utf-8 -*-
import re
import time
import datetime
import unittest
from mock import patch, call, ANY

from ldap_expire_notify.channel import email


class TestEmailChannel(unittest.TestCase):
    def setUp(self):
        self.c = email.EmailChannel('test', {
            'threshold': 10,
            'workers': 1,
            'subject': '{{ ldap.uid | first }} password expiring',
            'recipient': '{{ ldap.mail | first}}',
            'from': '{{ ldap.mail | first}}',
            'body': '{{ dn }}',
        })
        self.c.server = 'smtp.test.com'

    def tearDown(self):
        self.c.stop()

    def test_init_ko(self):
        with self.assertRaisesRegex(ValueError, '^Required field \w+ is missing'):
            c = email.EmailChannel('email-test', {
                'threshold': 1,
                'workers': 1,
            })

    def test_init_ok(self):
        self.assertEqual(self.c.server, 'smtp.test.com')
        self.assertIsNotNone(self.c.subject_tmpl)
        self.assertIsNotNone(self.c.body_tmpl)
        self.assertIsNotNone(self.c.recipient)
        self.assertIsNotNone(self.c.from_)

    @patch("smtplib.SMTP")
    def test_start(self, smtp_mock):
        self.c.start()
        for w in self.c.workers:
            self.assertIsInstance(w, email.EmailWorker)
            self.assertEqual(w.channel, self.c)

    @patch("smtplib.SMTP")
    def test_worker_notify(self, smtp_mock):
        ret = {
            'vcabezas@test.com': (250, 'Requested mail action okay, completed'),
        }

        instance = smtp_mock.return_value
        instance.sendmail.return_value = ret

        self.c.start()
        w = self.c.workers[0]
        msg_data = {
            'dn': 'uid=vcabezas,ou=people,o=test',
            'expiration': datetime.datetime.now(),
            'ldap': {
                'uid': ['vcabezas'],
                'mail': ['vcabezas@example.com'],
            },
        }
        w.notify(msg_data)

        self.assertEqual(instance.sendmail.call_count, 1)
        self.assertEqual(instance.sendmail.mock_calls,
            [call(msg_data['ldap']['mail'][0], [msg_data['ldap']['mail'][0]], ANY)],
        )
