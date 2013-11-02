#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import cgitb
import json
import os
import urlparse
from common import  authorize
import redis
import traceback
from common.web import UserDatabase

import datetime

from dateutil import parser

cgitb.enable()


r = redis.Redis()


def log(msg, channel='constellations'):
    r.publish(channel, msg)


def check_time_range(now, t1, t2):
    """
    Returns True if now is between t1 and t2. Times are expressed
    in UTC strings
    """

    task_start = parser.parse(t1)
    task_stop = parser.parse(t2)
    start_age = (now - task_start).total_seconds()
    end_age = (now - task_stop).total_seconds()

    task_time_valid = start_age > 0 and end_age < 0

    return task_time_valid


def get_user_tasks(tasks):
    """
    Returns the next available task
    """

    latest_tasks = []
    for task in tasks:
        if task['task_state'] == 'stopped':
            latest_tasks.append(task)

    for task in tasks:
        if task['task_state'] in ['running', 'stopping', 'starting']:
            latest_tasks.append(task)
            return latest_tasks

    now = datetime.datetime.utcnow()
    for task in tasks:
        if task['task_state'] in ['ready']:
            t1 = task['local_start']
            t2 = task['local_stop']
            task_time_valid = check_time_range(now, t1, t2)

            if task_time_valid:
                latest_tasks.append(task)
                return latest_tasks

    return latest_tasks


def clean_constellation_data(constellation, role):
    """
    Remove data from the constellation to avoid cheating in the VRC
    """
    constellation.pop("constellation_directory")
    # remove tasks data
    tasks = constellation.pop('tasks')
    # and replace with a censored version
    constellation['tasks'] = []

    if role == 'user':
        tasks = get_user_tasks(tasks)

    for task in tasks:
        t = {'task_title': task['task_title'],
             'task_state': task['task_state'],
             'task_id': task['task_id'],
             'task_message': task['task_message']}
        constellation['tasks'].append(t)
    return constellation


def get_constellation(constellation_name, role):
    try:
        key = 'cloudsim/' + constellation_name
        log("get_constellation %s" % key)
        s = r.get(key)
        c = json.loads(s)
        constellation = clean_constellation_data(c, role)
        return constellation
    except Exception, e:
        tb = traceback.format_exc()
        log("get_constellation ex: %s traceback:  %s" % (e, tb))
        return None
    return None


def list_constellations(role):
    constellations = []
    for key in r.keys():
        toks = key.split('cloudsim/')
        if len(toks) == 2:
            constellation_name = toks[1]
            c = get_constellation(constellation_name, role)
            if c:
                log(constellation_name)
                constellations.append(c)
    return constellations


def get_constellation_from_path():
    try:
        constellation = os.environ['PATH_INFO'].split('/')[1]
        return constellation
    except:
        return ""


def get_query_param(param):
    qs = os.environ['QUERY_STRING']
    params = urlparse.parse_qs(qs)
    p = params[param][0]
    return p

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)

method = os.environ['REQUEST_METHOD']

print('Content-type: application/json')
print("\n")

if method == 'GET':
    s = None
    log("[GET] Constellations")
    try:
        constellation = get_constellation_from_path()
        log("%s, role: %s" % (constellation, role))
        if len(constellation) > 0:
            s = get_constellation(role, constellation)
        else:
            log("listing all constellations")
            l = list_constellations(role)
            s = json.dumps(l)

    except Exception, e:
        s = "%s" % e

    print("%s" % s)
    exit(0)


d = {}
d['username'] = email


if role not in ['admin']:
    d['role'] = role
    d['error'] = 'Insufficient privileges "%s"' % role
    s = json.dumps(d)
    print("%s" % s)
    exit(0)

if method == 'DELETE':
    d['command'] = 'terminate'
    d['constellation'] = get_constellation_from_path()


if method == 'PUT':
    d['command'] = 'update'
    d['constellation'] = get_constellation_from_path()


if method == 'POST':
    d['command'] = 'launch'
    d['cloud_provider'] = get_query_param('cloud_provider')
    d['configuration'] = get_query_param('configuration')


s = json.dumps(d)
r.publish('cloudsim_cmds', s)
print("%s" % s)
