# -*- coding: utf-8 -*-

import click
from click.testing import CliRunner

from ldap_expire_notify import cli


# Base testing ensuring cli's --help work
def test_main():
    runner = CliRunner()
    result = runner.invoke(cli.main, ['--help'])
    assert result.exit_code == 0


def test_check_channels():
    runner = CliRunner()
    result = runner.invoke(cli.check_channels, ['--help'])
    assert result.exit_code == 0
