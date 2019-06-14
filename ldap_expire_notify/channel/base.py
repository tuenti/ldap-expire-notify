# -*- coding: utf-8 -*-

import threading
import logging
import datetime
from queue import Queue

logger = logging.getLogger('ldap-expire-notify')


class Channel(object):
    __required_conf__ = []

    def __init__(self, name, configuration):
        self.workers = []
        self.num_workers = int(configuration.get('workers', 10))
        self.threshold = int(configuration['threshold'])
        self.queue = Queue()
        self.name = name
        self.check_configuration(configuration)

    def check_and_notify(self, expiration_time, user_dn, user_data):
        now = datetime.datetime.now()
        if expiration_time - datetime.timedelta(seconds=self.threshold) < now:
            logger.debug(
                'DN=%s "%s" notification threshold reached (%s < NOW[%s])',
                user_dn,
                self.name,
                expiration_time - datetime.timedelta(seconds=self.threshold),
                now,
            )
            logger.info('Notifying %s via %s', user_dn, self.name)
            self.queue.put({
                'dn': user_dn,
                'ldap': user_data,
                'expiration': expiration_time,
            })
            return True

        return False

    def check_configuration(self, config):
        for k in self.__required_conf__ + ['threshold']:
            if k not in config:
                raise ValueError('Required field {} is missing for channel {}'.format(
                    k, self.name))

    def start(self):
        logger.debug('Starting %d %s workers', self.num_workers, self.name)
        for _ in range(self.num_workers):
            w = self.new_worker()
            w.start()
            self.workers.append(w)

    def stop(self):
        logger.debug('Stopping %s workers', self.name)
        for _ in self.workers:
            self.queue.put(None)
        if len(self.workers) > 0:
            logger.debug('Joining %s workers', self.name)
            self.queue.join()
        self.workers = []


class ChannelWorker(threading.Thread):
    def __init__(self, channel, queue):
        super(ChannelWorker, self).__init__()
        self.channel = channel
        self.queue = queue
        # This is for informative logging
        self.name = '{}-{}'.format(self.__class__.__name__, self.name.split('-')[-1])

    def log(self, msg, level=logging.INFO):
        logger.log(level, '%s: %s', self.name, msg)

    def run(self):
        while True:
            task = self.queue.get()
            if task is None:  # Notify tasks are done via sending None to the worker threads
                self.log('Received finish signal', logging.DEBUG)
                self.queue.task_done()
                break

            try:
                task['threshold'] = self.channel.threshold
                task['threshold_hour'] = task['threshold'] / 3600
                task['threshold_day'] = task['threshold_hour'] / 24
                self.notify(task)
            except Exception as e:
                logger.exception('Unable to notify task %s', task)
            finally:
                self.queue.task_done()
