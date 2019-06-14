# -*- coding: utf-8 -*-


import pytest
from mock import patch

from ldap_expire_notify import utils


@pytest.fixture(scope='function')
def app_channels():
    with patch('smtplib.SMTP'):
        app_channels = utils.start_channels('channels/', 'smtp.example.org', None, None, False, False)
        yield app_channels
        utils.stop_channels(app_channels)

