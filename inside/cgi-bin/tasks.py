#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
import os
import urlparse
from common import  authorize
import redis

cgitb.enable()
r = redis.Redis()

def log(msg):
    r.publish('tasks', msg)

def _domain(email):
    domain = email.split('@')[1]
    return domain

def get_task(email, constellation_name, task_id):

    try:
        key = 'cloudsim/' + constellation_name
       
        s = r.get(key)
        c = json.loads(s)
        log("c %s" % c)
        
        domain = _domain(c['username'])
        authorised_domain = _domain(email)
        
        
        if domain == authorised_domain:
            tasks = c['tasks']
            for task in tasks:
                if task['task_id'] == task_id:
                    return task
        return None
    except:
        return None

def parse_path():
    try:
        toks = os.environ['PATH_INFO'].split('/')
        constellation = toks[1]
        if len(toks) == 2:
            return constellation, None
        task_id = toks[2]
        return constellation, task_id
    except:
        return None, None


def get_query_param(param):
    qs= os.environ['QUERY_STRING']
    params = urlparse.parse_qs(qs)
    p = params[param][0]
    return p

email = authorize()
method = os.environ['REQUEST_METHOD']

print('Content-type: application/json')
print("\n")

constellation, task_id = parse_path()

if method == 'GET':
    s = None
    log("tasks")
    try:
        if len(constellation) > 0:
            domain = _domain(email)
            key = "cloudsim/"+ constellation
            task = get_task(email, constellation, task_id)
            s = json.dumps(task)
    except Exception, e:
        s = "%s" % e
        
    print( s)
    exit(0)

d = {}

if method == 'DELETE':
    d['command'] = 'delete_task'
    d['constellation'] = constellation
    d['task_id'] = task_id    



if method == 'PUT':
    d['command'] = 'update_task'
    d['task_id'] = task_id  

if method == 'POST':
    d['command'] = 'create_task'

s = json.dumps(d)
r.publish('cloudsim_cmds', s)
print("%s" % s)