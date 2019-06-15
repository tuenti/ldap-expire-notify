# -*- coding: utf-8 -*-

import os
import logging
import json
import yaml

try:
    from yaml import CLoader as YAMLLoader
except ImportError:
    from yaml import Loader as YAMLLoader


from .email import EmailChannel
from .webhook import WebhookChannel

logger = logging.getLogger('ldap-expire-notify')


def parse(path):
    data = {'channels': {}}
    if os.path.isfile(path):
        data = parse_file(path)
    elif os.path.isdir(path):
        for root, _, files in os.walk(path):
            for f in files:
                abs_path = os.path.join(root, f)
                channel = parse_file(abs_path)
                if channel:
                    data['channels'].update(channel.get('channels', {}))

    if len(data.get('channels', {})) == 0:
        logger.error('No channel information found when parsing configuration')
        raise ValueError('No configuration found')

    channels = {}
    for name, info in data['channels'].items():
        channel = _build_channel(name, info)
        if channel:
            channels[name] = channel

    return channels


def _build_channel(name, info):
    kind = info.get('kind')
    if kind == 'email':
        return EmailChannel(name, info)
    elif kind == 'webhook':
        return WebhookChannel(name, info)
    else:
        logger.warning(
            'Channel %s kind %s is invalid, must be one of email or webhook',
            name,
            kind,
        )
    return None


def parse_file(path):
    logger.info('Parsing file "%s"', path)
    base, ext = os.path.splitext(path)
    if ext in ['.yaml', '.yml']:
        return yaml.load(open(path, 'r'), Loader=YAMLLoader)
    elif ext == '.json':
        return json.load(open(path, 'r'))
    else:
        logger.warning('Unknown extension %s for file %s, ignoring...', ext, path)
        return None
