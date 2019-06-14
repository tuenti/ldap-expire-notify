# -*- coding: utf-8 -*-
# Setup.py inspired by Django setup.py script
# https://github.com/django/django/blob/master/setup.py

import os

from setuptools import find_packages, setup
from distutils.sysconfig import get_python_lib

import pip
if tuple(map(int, pip.__version__.split('.'))) >= (10, 0, 0):
    from pip._internal.download import PipSession
    from pip._internal.req import parse_requirements
else:
    from pip.download import PipSession
    from pip.req import parse_requirements
from ldap_expire_notify import meta

REQUIRED_PYTHON = (3, 5)

EXCLUDE_FROM_PACKAGES = []

def graceful_read(fname):
    try:
        with open(os.path.join(os.path.dirname(__file__), fname)) as f:
            return f.read()
    except Exception:
        return ''

install_requires_g = parse_requirements("requirements.txt", session=PipSession())
install_requires = [str(ir.req) for ir in install_requires_g]

tests_require_g = parse_requirements("requirements-tests.txt", session=PipSession())
tests_require = [str(ir.req) for ir in tests_require_g]

docs_require_g = parse_requirements("requirements-docs.txt", session=PipSession())
docs_require = [str(ir.req) for ir in docs_require_g]

setup(
    name='ldap-expire-notify',
    version=meta.version,
    python_requires='>={}.{}'.format(*REQUIRED_PYTHON),
    author=meta.author,
    author_email=meta.author_email,
    description=meta.description,
    long_description=graceful_read('README.rst'),
    license='Apache',
    packages=find_packages(exclude=EXCLUDE_FROM_PACKAGES),
    entry_points={'console_scripts': [
        'ldap-expire-notify = ldap_expire_notify.cli:main',
        'ldap-expire-check-channels = ldap_expire_notify.cli:check_channels',
    ]},
    install_requires=install_requires,
    extras_require={
        'tests': tests_require,
        'docs': docs_require,
    },
    zip_safe=False,
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: System Administrators',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3 :: Only',
    ]
)
