#!/usr/bin/env python3

from datetime import datetime, timedelta
from calendar import monthrange
from dateutil import relativedelta, parser
import json
import requests
import configparser
import argparse
import os.path
import sys

"""
Examine a configuration file for upcoming big events, and post
to slack with how long is left before they happen.

Usage:
countdown.py

Requires a config file, such as config.ini


"""

# TODO:
# encoding of alert intervals - high, medium, low
# So the alerts can get more frequent the closer we get
# to an event


def slack_post(message, url, channel):
    if debug:
        return(200, 'ok')
    payload = dict()
    payload['text'] = message
    payload['username'] = 'Reminders'
    payload['channel'] = channel

    r = requests.post(url, data=json.dumps(payload))
    return (r.status_code, r.text)


def time_until(target_date):
    """
    time_until: Argument target_date as a datetime object
    returns a string describing how long until target_date
    is reached
    """
    cursor = datetime.now()

    months = 0
    while cursor <= target_date:
        days_this_month = monthrange(cursor.year, cursor.month)[1]
        cursor = cursor + timedelta(days=days_this_month)
        months += 1

    # we overshoot. fix
    cursor = cursor - timedelta(days=days_this_month)
    months -= 1

    # it's either dateutil or strip off the microseconds ourselves.
    delta = relativedelta.relativedelta(target_date, cursor)

    display_string = str()
    # hide the months if zero
    if months > 0:
        display_string += "{} months ".format(months)

    display_string += "{} days {}:{:02d}:{:02d}".format(
        delta.days,
        delta.hours,
        delta.minutes,
        delta.seconds
    )
    return display_string


# End function definitions


argparser = argparse.ArgumentParser(
    description='Send reminder countdowns to Slack')
argparser.add_argument(
    '-c', '--config',
    default='config.ini', help='configuration file')
argparser.add_argument(
    '-d', '--debug',
    action="store_true", help='Debug mode, do not post to Slack')
args = argparser.parse_args()

debug = args.debug

if not os.path.isfile(args.config):
    print("Unable to find config file {}".format(args.config))
    sys.exit(1)

config = configparser.ConfigParser()
config.read(args.config)

# For each configuration section, check whether we need to send a
# message, generate that message and post it.
for target in config.sections():
    timestamp = config.get(target, 'date', fallback="2014-01-01T00:00:00")
    description = config.get(target, 'message', fallback="")

    dt = parser.parse(timestamp)

    # Skip events that have already happened or with no description
    if dt < datetime.now() or len(description) < 1:
        continue

    message = "{} in {}".format(description, time_until(dt))

    if debug:
        print(message)

    (response_code, response_text) = slack_post(
        message,
        url=config[target]['slack_hook_url'],
        channel=config[target]['channel']
    )
    if response_code != 200:
        print("""Posting failed
Sending message: "{message}" to channel {channel} at {url}
Failed with response code {code}: {text}
""".format(
            message=message,
            url=config[target]['slack_hook_url'],
            channel=config[target]['channel'],
            code=response_code,
            text=response_text,
        ))
        break
