# -*- coding: utf-8 -*-

import logging
import jinja2
import requests
import time

from .base import Channel, ChannelWorker

logger = logging.getLogger('ldap-expire-notify')


class WebhookChannel(Channel):
    __required_conf__ = ['url']

    def __init__(self, name, configuration):
        super(WebhookChannel, self).__init__(name, configuration)
        self.url = jinja2.Template(configuration['url'])
        self.method = str.upper(configuration.get('method', 'get'))
        self.throttle_code = int(configuration.get('throttle_code', '429'))
        self.throttle_retries = int(configuration.get('throttle_retries', '5'))
        self.throttle_max_sleep = int(configuration.get('throttle_max_sleep', '30'))
        self.body_tmpl = jinja2.Template(configuration.get('body', ''))
        self.headers = configuration.get('headers', [])

        if self.throttle_retries < 1:
            raise ValueError('throttle_retries must be greater than 0, got {}'.format(
                self.throttle_retries))

        if self.throttle_max_sleep < 1:
            raise ValueError('throttle_max_sleep must be greater than 0, got {}'.format(
                self.throttle_max_sleep))

    def new_worker(self):
        return WebhookWorker(
            self,
            self.queue,
            self.throttle_code,
            self.throttle_retries,
            self.throttle_max_sleep,
            self.url,
            self.body_tmpl,
            self.method,
            self.headers,
        )


class WebhookWorker(ChannelWorker):
    DEFAULT_TIMEOUT = 10

    def __init__(self,
            channel,
            queue,
            throttle_code,
            throttle_retries,
            throttle_max_sleep,
            url_tmpl,
            body_tmpl,
            method,
            headers
    ):
        super(WebhookWorker, self).__init__(channel, queue)
        self.throttle_code = throttle_code
        self.throttle_retries = throttle_retries
        self.throttle_max_sleep = throttle_max_sleep
        self.url_tmpl = url_tmpl
        self.body_tmpl = body_tmpl
        self.method = method
        self.headers = headers

    def notify(self, data):
        url = self.url_tmpl.render(data)
        body = None
        if self.body_tmpl:
            body = self.body_tmpl.render(data)
        self.log('Sending Webhook to {} ({}) [{}]'.format(
            url,
            self.method,
            ' '.join(self.headers),
        ), logging.DEBUG)

        sleep = 1
        for i in range(self.throttle_retries):
            r = requests.request(self.method,
                url,
                data=body,
                headers=self.headers,
                timeout=self.DEFAULT_TIMEOUT
            )
            if r.status_code == self.throttle_code:
                self.log('Got throttle_code {}, sleeping {} seconds, {} out of {} retries'.format(
                    r.status_code,
                    sleep,
                    i + 1,
                    self.throttle_retries,
                ))
                time.sleep(sleep)
                sleep = min(2 * sleep, self.throttle_max_sleep)
            else:
                self.log('Got {}: {}'.format(r.status_code, r.content), logging.DEBUG)
                break
        else:
            raise RuntimeError('All requests to {} were throttled'.format(url))
