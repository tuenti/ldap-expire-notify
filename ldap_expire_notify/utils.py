# -*- coding: utf-8 -*-

import sys
import logging
import datetime

from . import channel

logger = logging.getLogger('ldap-expire-notify')


class MissingModify(ValueError):
    pass


def die(msg, code=1):
    logger.exception(msg)
    sys.exit(code)


def start_channels(path, smtp_server, smtp_user, smtp_pwd, smtp_ssl, smtp_starttls):
    channels = channel.parse(path)

    for cinfo in channels.values():
        if isinstance(cinfo, channel.email.EmailChannel):
            cinfo.server = smtp_server
            cinfo.user = smtp_user
            cinfo.pwd = smtp_pwd
            cinfo.ssl = smtp_ssl
            cinfo.starttls = smtp_starttls
        cinfo.start()

    return channels


def get_user_expiration_time(user_modification, modify_format, max_age):
    if not user_modification:
        raise MissingModify('Modification field is not present')
    try:
        pwd_modification = user_modification[0]
        modification_time = datetime.datetime.strptime(pwd_modification, modify_format)
    except ValueError:
        raise MissingModify('Unable to decode password modification time')

    expiration_time = modification_time + datetime.timedelta(seconds=max_age)
    return expiration_time


def stop_channels(channels):
    for cname, cinfo in channels.items():
        cinfo.stop()
