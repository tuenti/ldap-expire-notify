import pytest

from ldap_expire_notify import channel


def test_parse_file_json():
    r = channel.parse_file('channels/mail.test.json')

    assert 'email-test' in r['channels']


def test_parse_file_yaml():
    r = channel.parse_file('channels/webhook.test.yaml')

    assert 'webhook-test' in r['channels']


def test_parse_file_unknown():
    r = channel.parse_file('channels/webhook.test.yson')
    assert r == None


def test_parse_directory_ko():
    with pytest.raises(ValueError):
        r = channel.parse('/tmp/')

    with pytest.raises(ValueError):
        r = channel.parse('/non-existent-chan/')


def test_parse_directory():
    r = channel.parse('channels/')

    assert len(r) == 2
    assert 'email-test' in r
    assert 'webhook-test' in r


def test_parse_email():
    r = channel.parse('channels/mail.test.json')

    assert 'email-test' in r
    assert r['email-test'].name == 'email-test'
    assert r['email-test'].threshold == 259200000
    assert r['email-test'].subject_tmpl is not None
    assert r['email-test'].body_tmpl is not None
    assert r['email-test'].recipient is not None
    assert r['email-test'].from_ is not None


def test_parse_webhook():
    r = channel.parse('channels/webhook.test.yaml')

    assert 'webhook-test' in r
    assert r['webhook-test'].name == 'webhook-test'
    assert r['webhook-test'].threshold == 2592000000
    assert r['webhook-test'].url is not None
    assert r['webhook-test'].method == 'POST'
    assert r['webhook-test'].body_tmpl is not None
    assert 'Content-Type' in r['webhook-test'].headers
