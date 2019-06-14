SHELL=/bin/bash
USER := $(shell whoami)

# Makefile taken from https://github.com/Netflix/lemur, thx Netflix guys

develop: up-reqs
	@echo "--> Installing dependencies"
	pip install "setuptools>=0.9.8"
	# order matters here, base package must install first
	pip install -e .
	pip install "file://`pwd`#egg=ldap-expire-notify[tests]"
	pip install "file://`pwd`#egg=ldap-expire-notify[docs]"

clean:
	@echo "--> Cleaning pyc files"
	find . -name "*.pyc" -delete
	@echo ""

dev-docs:
	pip install -r docs/requirements.txt

testloop:
	pip install pytest-xdist
	coverage run --source ldap_expire_notify -m py.test

test: lint
	@echo "--> Running tests"
	coverage run --source ldap_expire_notify -m py.test
	@echo ""

lint:
	@echo "--> Linting files"
	PYFLAKES_NODOCTEST=1 flake8 ldap_expire_notify
	@echo ""

coverage: test
	coverage html

publish:
	python setup.py sdist bdist_wheel upload

up-reqs:
ifndef VIRTUAL_ENV
    $(error Please activate virtualenv first)
endif
	@echo "--> Updating Python requirements"
	pip install --upgrade pip
	pip install --upgrade pip-tools
	pip-compile --output-file requirements.txt requirements.in -U --no-index
	pip-compile --output-file requirements-docs.txt requirements-docs.in -U --no-index
	pip-compile --output-file requirements-tests.txt requirements-tests.in -U --no-index
	@echo "--> Done updating Python requirements"
	@echo "--> Removing python-ldap from requirements-docs.txt"
	grep -v "python-ldap" requirements-docs.txt > tempreqs && mv tempreqs requirements-docs.txt
	@echo "--> Installing new dependencies"
	pip install -e .
	@echo "--> Done installing new dependencies"
	@echo ""

install:
	pip install --upgrade pip
	pip install --upgrade pip-tools
	pip-compile --output-file requirements.txt requirements.in -U --no-index
	@echo "--> Done updating requirements"
	pip install .
	@echo "--> Done installing"
	@echo ""

.PHONY: develop dev-docs build clean test testloop test lint coverage publish
