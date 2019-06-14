# -*- coding: utf-8 -*-

import logging
import click
import click_log
import ldap
from collections import defaultdict

from . import database
from . import channel
from . import utils

logger = logging.getLogger('ldap-expire-notify')
click_log.basic_config(logger)


@click.command()
@click.option('--host', '-H', envvar='LDAP_HOST',
        default='ldap://localhost', help='LDAP server host, must include protocol')
@click.option('--port', '-p', envvar='LDAP_PORT',
        default=389, type=int, help='LDAP server port')
@click.option('--bind-dn', '-D', envvar='LDAP_BIND_DN',
        required=True, help='DN used to bind to LDAP server')
@click.option('--pwd', envvar='LDAP_BIND_PWD',
        required=True, help='Password used to bind to LDAP server')
@click.option('--base-dn', '-b', envvar='LDAP_BASE_DN',
        required=True, help='Base DN used to perform searches in LDAP server')
@click.option('--starttls/--no-starttls', envvar='LDAP_STARTTLS',
        default=False, help='Use StartTLS feature when connecting to LDAP server')
@click.option('--ignorecert/--no-ignore-cert', envvar='LDAP_IGNORE_CERT',
        default=False, help='Ignore LDAP Certificate when binding (not recommended)')
@click.option('--users-query', '-q', envvar='LDAP_QUERY',
        default='(uid=*)', help='Query used to retrieve all users')
@click.option('--user-attrs', '-f', multiple=True,
        default=['*', '+'], help='User attributes to be retrieved')
@click.option('--query-scope', envvar='LDAP_SCOPE',
        type=click.Choice(['BASE', 'ONELEVEL', 'SUBTREE']),
        default='SUBTREE', help='Query used to retrieve all users')
@click.option('--modify-attr', '-e',
        default='pwdChangedTime', help='Attribute where password modification time is stored')
@click.option('--modify-format',
        default='%Y%m%d%H%M%SZ', help='Modification time strptime format')
@click.option('--pwd-max-age', '-M', type=int,
        default=31536000, help='Maximum password age in seconds')
@click.option('--smtp-server', envvar='SMTP_SERVER',
        help='SMTP server used to send emails')
@click.option('--smtp-user', envvar='SMTP_USER',
        help='User used to login into SMTP server')
@click.option('--smtp-pwd', envvar='SMTP_PWD',
        help='SMTP User password')
@click.option('--smtp-ssl/--no-smtp-ssl', envvar='SMTP_SSL',
        default=False, help='Use SMTP SSL connection')
@click.option('--smtp-starttls/--no-smtp-starttls', envvar='SMTP_STARTTLS',
        default=False, help='Use STARTTLS SMTP connection')
@click.option('--channels', '-c', envvar='CHANNELS', required=True, help='Channels configuration, \
        can be a json/yaml file or a folder containing json/yaml files')
@click_log.simple_verbosity_option(logger)
def main(**kwargs):

    hidden_params = ['pwd', 'smtp_pwd']
    for k, v in kwargs.items():
        v = '*****' if k in hidden_params else v
        logger.info('Parameter %-15s => %s', k, v)

    logger.info('Connecting to LDAP Directory')
    try:
        ldap_db = database.LDAPDatabase(
            kwargs.get('host'),
            kwargs.get('port'),
            kwargs.get('bind_dn'),
            kwargs.get('pwd'),
            kwargs.get('base_dn'),
        )
    except ValueError:
        utils.die('Invalid variable connecting to LDAP')
    except ldap.LDAPError:
        utils.die('Unable to connect to LDAP')

    try:
        channels = utils.start_channels(
            kwargs.get('channels'),
            kwargs.get('smtp_server'),
            kwargs.get('smtp_user'),
            kwargs.get('user_pwd'),
            kwargs.get('smtp_ssl'),
            kwargs.get('smtp_starttls')
        )
    except Exception:
        utils.die('Unable to start channels')

    modify_field = kwargs.get('modify_attr')
    modify_format = kwargs.get('modify_format')
    max_age = kwargs.get('pwd_max_age')

    notifications = defaultdict(int)
    users = 0  # Avoid issues with empty result sets
    db_users = ldap_db.get_users(
        kwargs.get('users_query'),
        kwargs.get('query_scope'),
        kwargs.get('user_attrs'),
    )
    for users, (user_dn, user_data) in enumerate(db_users, 1):
        try:
            expiration_time = utils.get_user_expiration_time(
                user_data.get(modify_field),
                modify_format,
                max_age,
            )
        except utils.MissingModify as e:
            logger.error('User DN=%s: %s', user_dn, e)
            continue

        logger.info('DN=%s password will expire at %s', user_dn, expiration_time)

        for cname, cinfo in channels.items():
            if cinfo.check_and_notify(expiration_time, user_dn, user_data):
                notifications[cname] += 1

    logger.info('Processed %d users', users)

    for cname, cinfo in channels.items():
        logger.info('Sent %d notifications to %s channel', notifications[cname], cname)

    utils.stop_channels(channels)


@click.command()
@click.option('--channels', '-c', envvar='CHANNELS', required=True, help='Channels configuration, \
        can be a json/yaml file or a folder containing json/yaml files')
@click_log.simple_verbosity_option(logger)
def check_channels(**kwargs):
    channels = channel.parse(kwargs.get('channels'))
    for cname, cinfo in channels.items():
        logger.info('-' * 50)
        logger.info('Channel: %s', cname)
        logger.info('Kind: %s', cinfo.__class__.__name__)
        if isinstance(cinfo, channel.email.EmailChannel):
            logger.info('Recipient template: %s', cinfo.recipient)
            logger.info('Subject template: %s', cinfo.subject_tmpl)
        elif isinstance(cinfo, channel.webhook.WebhookChannel):
            logger.info('Method: %s', cinfo.method)
            logger.info('Headers: [%s]', ', '.join(cinfo.headers))
        logger.info('Body template: %s', cinfo.body_tmpl)
        logger.info('-' * 50)
