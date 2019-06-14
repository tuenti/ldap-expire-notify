LDAP Expire Notify
==================

`ldap-expire-notify` is a tool to notify your LDAP users when their password
is about to expire. It supports several kind of notification **channels**.


Features
--------

- Configure several notification **channels** with different thresholds.
- Currently supported channels include:
  - Email
  - Webhook

Installation
------------

Install ldap-expire-notify by running:

```
    pip install https://github.com/tuenti/ldap-exire-notify@v0.1.0#egg=ldap-expire-notify
```

How to use
----------

For a complete list of parameters run `ldap-expire-notify --help`

```
$ ldap-expire-notify --help
Usage: ldap-expire-notify [OPTIONS]

Options:
  -H, --host TEXT                 LDAP server host, must include protocol
  -p, --port INTEGER              LDAP server port
  -D, --bind-dn TEXT              DN used to bind to LDAP server  [required]
  --pwd TEXT                      Password used to bind to LDAP server
                                  [required]
  -b, --base-dn TEXT              Base DN used to perform searches in LDAP
                                  server  [required]
  --starttls / --no-starttls      Use StartTLS feature when connecting to LDAP
                                  server
  --ignorecert / --no-ignore-cert
                                  Ignore LDAP Certificate when binding (not
                                  recommended)
  -q, --users-query TEXT          Query used to retrieve all users
  -f, --user-attrs TEXT           User attributes to be retrieved
  --query-scope [BASE|ONELEVEL|SUBTREE]
                                  Query used to retrieve all users
  -e, --modify-attr TEXT          Attribute where password modification time
                                  is stored
  --modify-format TEXT            Modification time strptime format
  -M, --pwd-max-age INTEGER       Maximum password age in seconds
  --smtp-server TEXT              SMTP server used to send emails
  --smtp-user TEXT                User used to login into SMTP server
  --smtp-pwd TEXT                 SMTP User password
  --smtp-ssl / --no-smtp-ssl      Use SMTP SSL connection
  --smtp-starttls / --no-smtp-starttls
                                  Use STARTTLS SMTP connection
  -c, --channels TEXT             Channels configuration, can be a json/yaml
                                  file or a folder containing json/yaml files
                                  [required]
  -v, --verbosity LVL             Either CRITICAL, ERROR, WARNING, INFO or
                                  DEBUG
  --help                          Show this message and exit.
```

How to configure channels
-------------------------

Channel configuration is passed via the flags `-c` or `--channels`. It can be both
a yaml/json file or a folder containing yaml/json files. If passing a folder as parameter
all channels found in files will be merged and used.

Channels file syntax
--------------------

All channel files must have the following syntax:

```yaml
---
  channels:
    channel-unique-name:
      kind: email|webhook (Required)
      threshold: Notification threshold in seconds (Required)
      workers: Number of threads to be spawn for the channel (default: 10)
```

Depending on the kind, the rest of parameters may vary, following is a example
configuration for email channel:

```yaml
---
  channels:
    email-channel:
      kind: email
      workers: 3
      threshold: 604800 # 1 week
      recipient: '{{ ldap.mail | first }}' # Required, jinja2 template syntax
      subject: '{{ ldap.uid | first }} for password is going to expire' # Required, jinja2 template syntax
      from: 'admin@example.com' # Required, jinja2 template syntax
      body: | # Required, jinja2 template syntax
        <html>
          <body>
            <h3> This is LDAP expire password notification </h3>
            <p> Hi {{ ldap.givenName | first}}, your LDAP password will expire at {{ expiration }} days.</p>
            <p> Contact your system administrator to update it </p>
          </body>
        </html>
```

Following is a example configuration for webhook channel:

```yaml
  channels:
    webhook-channel:
      kind: webhook
      workers: 3
      threshold: 604800 # 1 week
      throttle_code: 429 # Optional, default: 429
      throttle_retries: 10 # Optional, default: 5
      throttle_max_sleep: 10 # Optional, default: 30
      headers: # Optional, must be a hash map
        Content-Type: application/json
      body: | # Optional, jinja2 template syntax
        {
          "comment": "This is a test webhook that will POST a JSON body and some headers",
          "msg": "Hi {{ ldap.cn | first }}, your LDAP password will expire in the next {{ threshold_day }} days or less",
          "recipient": "@{{ ldap.slack | first }}"
        }
      url: 'http://httpbin.org/anything/{{ ldap.uid | first }}' # Required, jinja2 template syntax
      method: post  # Optional, default: get
```

**About throttling**
If `throttle_code` is returned from remote endpoint as an HTTP status code, throttling mechanism
will be triggered. It implements exponential backoff starting from 1 seconds and applying a factor
of 2 until `throttle_max_sleep`. A total of `throttle_retries` iterations will be done before
failing.


How tool works
--------------

For every entry returned by LDAP using `--users-query`, the expiration time
is computed using the `--modify-attr` that should be present in the the same entry,
if the current time substracted expiration time is **less than or equal** `channel.threshold`,
the a notification is sent.

Which fields are available in templates
---------------------------------------

For all setting fields that are jinja2 compatible, the following fields are exported:

- `expiration`: Is the expiration time. It is an instance of `datetime.datetime`.
- `dn`: This is the user DN from LDAP.
- `threshold`: Is the channel threshold in seconds
- `threshold_hour`: Is the channel threshold in hours
- `threshold_day`: Is the channel threshold in days
- `ldap`: This is the the user LDAP entry, so any user's attribute can be used. \
  Note that LDAP library returns a list for every attribute but usually only 1 value is
  present, so to use the first element the `| first` jinja2 filter may be used.

Developing
----------

To setup developing environment you'll need to setup a `virtualenv`.

Once your `virtualenv` is setup and activated, run:

```
  make develop
```

This will install all dependencies needed.


Contribute
----------

- Issue Tracker: github.com/tuenti/ldap-expire-notify/issues
- Source Code: github.com/tuenti/ldap-expire-notify

Support
-------

If you are having issues, please let us know by opening a Github Issue.

License
-------

The project is licensed under the Apache license.
