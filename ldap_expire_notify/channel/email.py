# -*- coding: utf-8 -*-

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jinja2
from bs4 import BeautifulSoup

from .base import Channel, ChannelWorker

logger = logging.getLogger('ldap-expire-notify')


class EmailChannel(Channel):
    __required_conf__ = ['subject', 'body', 'recipient', 'from']

    def __init__(self, name, configuration):
        super(EmailChannel, self).__init__(name, configuration)
        self.server = None
        self.user = None
        self.pwd = None
        self.ssl = False
        self.starttls = False
        self.subject_tmpl = jinja2.Template(configuration['subject'])
        self.body_tmpl = jinja2.Template(configuration['body'])
        self.recipient = jinja2.Template(configuration['recipient'])
        self.from_ = jinja2.Template(configuration['from'])

    def new_worker(self):
        return EmailWorker(
            self,
            self.queue,
            self.server,
            self.user,
            self.pwd,
            self.ssl,
            self.starttls,
            self.subject_tmpl,
            self.body_tmpl,
            self.recipient,
            self.from_,
        )


class EmailWorker(ChannelWorker):
    DEFAULT_PORT = 25

    def __init__(self,
        channel,
        queue,
        server,
        user,
        pwd,
        ssl,
        starttls,
        subject_tmpl,
        body_tmpl,
        recipient,
        from_
    ):
        super(EmailWorker, self).__init__(channel, queue)
        self.server = server.split(':')[0]
        self.port = server.split(':')[-1] if ':' in server else self.DEFAULT_PORT
        self.user = user
        self.pwd = pwd
        self.ssl = ssl
        self.starttls = starttls
        self.subject_tmpl = subject_tmpl
        self.body_tmpl = body_tmpl
        self.recipient = recipient
        self.from_ = from_
        self.conn = None
        self._connect()

    def __del__(self):
        if self.conn:
            self.log('Closing SMTP connection', logging.DEBUG)
            self.conn.quit()
            self.conn = None

    def _connect(self):
        self.log('Connecting to SMTP server at {}'.format(self.server), logging.DEBUG)
        if not self.ssl:
            self.conn = smtplib.SMTP(self.server, self.port)
        else:
            self.conn = smtplib.SMTP_SSL(self.server)

        if self.user and self.pwd:
            self.conn.login(self.user, self.pwd)

        if self.starttls:
            self.conn.starttls()

    def notify(self, data):
        recipient = self.recipient.render(data)
        subject = self.subject_tmpl.render(data)
        body = self.body_tmpl.render(data)
        from_ = self.from_.render(data)
        self.log('Sending email notification ({}) [{}] to {} from {}'.format(
            subject,
            body,
            recipient,
            from_,
        ), logging.DEBUG)
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_
        msg['To'] = recipient
        msg.attach(MIMEText(BeautifulSoup(body, features="html.parser").get_text(), 'text'))
        msg.attach(MIMEText(body, 'html'))
        self.conn.sendmail(from_, [recipient], msg.as_string())
