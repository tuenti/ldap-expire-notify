import unittest

import os
import yaml
import mockldap
import ldap

from ldap_expire_notify import database

test_directory = yaml.load(open(os.path.join(os.path.dirname(__file__), 'directory.yaml'), 'r'))

class TestLDAPDatabase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mockldap = mockldap.MockLdap(test_directory)

    @classmethod
    def tearDownClass(cls):
        del cls.mockldap

    def setUp(self):
        self.mockldap.start()
        self.ldapobj = self.mockldap['ldap://localhost:389/']
        self.ldapiobj = self.mockldap['ldapi:///']

    def tearDown(self):
        self.mockldap.stop()
        del self.ldapobj

    def test_init_ko(self):
        with self.assertRaisesRegex(ValueError, '^Unknown protocol'):
            m = database.LDAPDatabase('http://ldap.example.org', 0, '', '', '')

        with self.assertRaisesRegex(ValueError, '^Unknown protocol'):
            m = database.LDAPDatabase('ldapi://', 0, '', '', '')

    def test_init_ok(self):
        m = database.LDAPDatabase(
            'ldap://localhost',
            389,
            'uid=binduser,ou=people,o=test',
            'bindpwd',
            'ou=people,o=test',
        )
        self.assertIsInstance(m, database.LDAPDatabase)
        self.assertEqual(m.base_dn, 'ou=people,o=test')

        self.assertEqual(self.ldapobj.methods_called(), ['initialize', 'simple_bind_s'])

        m = database.LDAPDatabase(
            'ldapi:///',
            389,
            'uid=binduser,ou=people,o=test',
            'bindpwd',
            'ou=people,o=test',
        )
        self.assertIsInstance(m, database.LDAPDatabase)
        self.assertEqual(m.base_dn, 'ou=people,o=test')

        self.assertEqual(self.ldapobj.methods_called(), ['initialize', 'simple_bind_s'])

    def test_string_record(self):
        a = {'a': [b'%d' % i for i in range(10)]}
        b = {'a': [ '%s' % i for i in range(10)]}

        self.assertEqual(database.LDAPDatabase.string_record(a), b)

    def test_parse_scope(self):
        self.assertEqual(database.LDAPDatabase.parse_scope('SUBTREE'), ldap.SCOPE_SUBTREE)
        self.assertEqual(database.LDAPDatabase.parse_scope('ONELEVEL'), ldap.SCOPE_ONELEVEL)
        self.assertEqual(database.LDAPDatabase.parse_scope('BASE'), ldap.SCOPE_BASE)

        with self.assertRaisesRegex(ValueError, '^Unknown LDAP query scope'):
            database.LDAPDatabase.parse_scope('FALSE')

    def test_get_users(self):
        m = database.LDAPDatabase(
            'ldap://localhost',
            389,
            'uid=binduser,ou=people,o=test',
            'bindpwd',
            'ou=people,o=test',
        )

        users = {dn: data for dn, data in m.get_users('(uid=*)')}
        self.assertEqual(len(users), len([1 for u in test_directory if 'uid=' in u]))

        self.assertEqual(self.ldapobj.methods_called(), ['initialize', 'simple_bind_s', 'search_s'])
