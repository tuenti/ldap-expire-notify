# -*- coding: utf-8 -*-

import re
import datetime
import logging

try:
    from io import StringIO
except ImportError:
    from StringIO import StringIO

import pytest
from mock import patch

from ldap_expire_notify import utils
from ldap_expire_notify import channel


def test_die():
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    logging.getLogger('ldap-expire-notify').addHandler(handler)
    with pytest.raises(SystemExit) as wrapped_e:
        utils.die('DIYING', 10)

    assert wrapped_e.value.code == 10
    assert re.search('DIYING', buf.getvalue())

    logging.getLogger('ldap-expire-notify').removeHandler(handler)


def test_start_channels(app_channels):
    assert len(app_channels) == 2
    assert 'webhook-test' in app_channels.keys()
    assert 'email-test' in app_channels.keys()
    assert isinstance(app_channels['webhook-test'], channel.webhook.WebhookChannel)
    assert isinstance(app_channels['email-test'], channel.email.EmailChannel)

    assert len(app_channels['webhook-test'].workers) == 10
    assert all(isinstance(w, channel.webhook.WebhookWorker) for w in app_channels['webhook-test'].workers)

    assert len(app_channels['email-test'].workers) == 10
    assert all(isinstance(w, channel.email.EmailWorker) for w in app_channels['email-test'].workers)


def test_stop_channels(app_channels):
    utils.stop_channels(app_channels)

    assert len(app_channels['webhook-test'].workers) == 0
    assert len(app_channels['email-test'].workers) == 0


def test_get_user_expiration_time():
    date_format = '%Y%m%d%H%M%SZ'
    max_age = 31536000
    now = datetime.datetime.now()

    with pytest.raises(utils.MissingModify):
        utils.get_user_expiration_time(None, date_format, max_age)

    with pytest.raises(utils.MissingModify):
        utils.get_user_expiration_time([], date_format, max_age)

    with pytest.raises(utils.MissingModify):
        utils.get_user_expiration_time(['123456780'], date_format, max_age)

    with pytest.raises(utils.MissingModify):
        utils.get_user_expiration_time(['123456780'], date_format, max_age)

    parsed = utils.get_user_expiration_time([now.strftime(date_format)], '%Y%m%d%H%M%SZ', max_age)
    assert parsed == (now + datetime.timedelta(seconds=max_age)).replace(microsecond=0)

    # Only first attribute should be taken
    parsed = utils.get_user_expiration_time([now.strftime(date_format), '1234567890'], '%Y%m%d%H%M%SZ', max_age)
    assert parsed == (now + datetime.timedelta(seconds=max_age)).replace(microsecond=0)
