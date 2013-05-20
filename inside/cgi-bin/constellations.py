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
import dateutil

cgitb.enable()


r = redis.Redis()


def log(msg, channel='constellations'):
    r.publish(channel, msg)


def get_user_tasks(tasks):
    """
    Returns the next available task
    """
    datetime.datetime.now()
    
    latest_tasks =[]
    for task in tasks:
        task 
        latest_tasks.append(task)
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


def get_constellation( constellation_name, role):
    try:
        key = 'cloudsim/' + constellation_name
        log("get_constellation %s" % key)
        s = r.get(key)
        c = json.loads(s)
        constellation = clean_constellation_data(c, role)
        return constellation
    except Exception, e:
        tb = traceback.format_exc()
        log("get_constellation traceback:  %s" % tb)
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
    #log("[GET] Constellations")
    try:
        constellation = get_constellation_from_path()
        # log("%s" % constellation)
        if len(constellation) > 0:
            s = get_constellation(email, constellation)
        else:
            # log("listing all constellations")
            l = list_constellations(email)
            s = json.dumps(l)

    except Exception, e:
        s = "%s" % e
        
    print("%s" % s)
    exit(0)

if method == 'PUT':
    # todo unsupported
    exit(0)

d = {}
d['username'] = email
d['type'] = 'launchers'

if method == 'DELETE':
    d['command'] = 'terminate'
    d['constellation'] = get_constellation_from_path()
    if role == 'user':
        d['error'] = "Insufficient privileges"
        s = json.dumps(d)
        print("%s" % s)
        exit(0)

if method == 'POST':
    d = {}
    d['username'] = email
    d['command'] = 'launch'
    d['configuration'] = get_query_param('configuration')


s = json.dumps(d)
r.publish('cloudsim_cmds', s)
print("%s" % s)