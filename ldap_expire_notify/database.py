# -*- coding: utf-8 -*-

import logging

import ldap

logger = logging.getLogger('ldap-expire-notify')

LDAP_SCOPES = {
    'BASE': ldap.SCOPE_BASE,
    'ONELEVEL': ldap.SCOPE_ONELEVEL,
    'SUBTREE': ldap.SCOPE_SUBTREE,
}


class LDAPDatabase(object):
    DEFAULT_ATTRS = ['*', '+']

    def __init__(self, host, port, bind_dn, bind_pwd, base_dn):
        if host == 'ldapi:///':
            self.server = host
        elif host.startswith('ldap://') or host.startswith('ldaps://'):
            self.server = '{host}:{port}/'.format(host=host, port=port)
        else:
            raise ValueError('Unknown protocol, host must start by one of ldap, ldaps or ldapi')

        logger.debug('Binding to %s@%s', bind_dn, self.server)
        self.conn = ldap.initialize(self.server)
        self.conn.simple_bind_s(bind_dn, bind_pwd)

        self.base_dn = base_dn

    @staticmethod
    def string_record(record):
        result = {}
        for k, v in record.items():
            result[k] = [vv.decode('utf-8') for vv in v]
        return result

    @staticmethod
    def parse_scope(scope):
        try:
            return LDAP_SCOPES[scope]
        except KeyError:
            raise ValueError('Unknown LDAP query scope: {}'.format(scope))

    def get_users(self, query='(uid=*)', scope='SUBTREE', attrs=None):
        logger.debug('Getting users from "%s" using "%s" filter', self.base_dn, query)
        # See https://docs.python-guide.org/writing/gotchas/#mutable-default-arguments to
        # understand the trick with `attrs`
        attrs = self.DEFAULT_ATTRS if attrs is None else attrs
        scope = self.parse_scope(scope)
        results = self.conn.search_s(self.base_dn, scope, query, attrs)
        for dn, entry in results:
            yield dn, self.string_record(entry)
