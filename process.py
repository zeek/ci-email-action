#! /usr/bin/env python3

import os
import sys
import json

def error(*args, **kwargs):
    # The GitHub UI seems to order stderr badly, so just use stdout.
    print(*args, file=sys.stdout, **kwargs)

def fatal(*args, **kwargs):
    error(*args, **kwargs)
    sys.exit(1)

def getenv(var):
    rval = os.environ[var]

    if not rval:
        fatal(f'Error: environment variable not usable: {var}')

    return rval

def check_env(*keys):
    err = False

    for k in keys:
        if k not in os.environ:
            err = True
            error(f'Error: environment variable not set: {k}')
            continue

        if not os.environ[k]:
            err = True
            error(f'Error: environment variable with no value: {k}')

        print(f'Found usable environment variable: {k}')

    if err:
        fatal(f'Error: required environment variables are not available')

def send_mail(subj, body):
    import smtplib
    from email.mime.text import MIMEText

    smtp_timeout = 30
    smtp_host = getenv('SMTP_HOST')
    smtp_port = getenv('SMTP_PORT')
    smtp_user = getenv('SMTP_USER')
    smtp_pass = getenv('SMTP_PASS')
    mail_from = getenv('MAIL_FROM')
    mail_to   = getenv('MAIL_TO')

    msg = MIMEText(body)
    msg['Subject'] = subj
    msg['From'] = mail_from
    msg['To'] = mail_to

    s = smtplib.SMTP(host=smtp_host, port=smtp_port, timeout=smtp_timeout)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(smtp_user, smtp_pass)
    s.sendmail(mail_from, [mail_to], msg.as_string())
    s.quit()

def skip(msg):
    print(msg)
    sys.exit(0)

check_env('GITHUB_EVENT_PATH',
          'CI_APP_NAME',
          'SMTP_HOST',
          'SMTP_PORT',
          'SMTP_USER',
          'SMTP_PASS',
          'MAIL_FROM',
          'MAIL_TO'
          )

ci_app_name = getenv('CI_APP_NAME')
event_payload_path = getenv('GITHUB_EVENT_PATH')

with open(event_payload_path) as epp:
    payload = json.load(epp)

if 'check_suite' not in payload:
    skip('Skip processing non-check_suite action')

if payload['action'] != 'completed':
    skip(f"Skip processing check_suite action type: {payload['action']}")

check_suite = payload['check_suite']
app = check_suite['app']

if app['name'] != ci_app_name:
    skip(f"Skip processing check_suite for app: {app['name']}")

pull_requests = check_suite['pull_requests']

if pull_requests:
    skip('Skip processing check_suite triggered via Pull Request')

conclusion = check_suite['conclusion']

if conclusion == 'success':
    # TODO: send mail if the last commit didn't have a successful conclusion
    skip('Skip processing successful check_suite')

print(f'Sending email for unsuccessful check_suite "{ci_app_name}"...')

repo = payload['repository']
repo_name = repo['name']
repo_url = repo['html_url']
branch = check_suite['head_branch']
sha = check_suite['head_sha']
short_sha = sha[:8]
commit_url = f'{repo_url}/commit/{sha}'

subject = f'[ci/{repo_name}] {ci_app_name}: Failed ({branch} - {short_sha})'
body = f'''
Unsuccessful result from CI:

    repo: {repo_url}
    branch: {branch}
    commit: {commit_url}
'''

send_mail(subject, body)
