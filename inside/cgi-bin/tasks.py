#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os
import urlparse
from common import authorize
import redis
from common.web import UserDatabase

cgitb.enable()
r = redis.Redis()


def log(msg):
    r.publish('tasks', msg)


# refuse the non deserving
def refuse_authorization():
    print('Content-type: application/json')
    print("\n")
    print("'Unauthorized'")
    exit(0)


def process_http_get(role, constellation, task_id):
    if method == 'GET':
        s = None
        log("GET task %s, role %s" % (task_id, role))
        try:
            if len(constellation) > 0:
                task = get_task(constellation, task_id)

                if role == "user":
                    if task['task_state'] == 'ready':
                        # Do not allow user to snoop the content of the task
                        # before it is executed:
                        refuse_authorization()
                s = json.dumps(task)
        except Exception as e:
            s = "%s" % e
        print('Content-type: application/json')
        print("\n")
        print(s)
    return s


def process_http_delete(role, constellation, task_id):
    if role == "user":
        refuse_authorization()
    d = {}
    d['command'] = 'delete_task'
    d['constellation'] = constellation
    d['task_id'] = task_id
    s = json.dumps(d)
    r.publish('cloudsim_cmds', s)
    print('Content-type: application/json')
    print("\n")
    print("%s" % s)


def get_task_params(constellation, command):
    d = {}

    d['command'] = command
    if command == 'update_task':
        # not present when creating a new task
        d['task_id'] = get_query_param("task_id")
    d['constellation'] = constellation
    d['task_title'] = get_query_param('task_title')
    d['ros_package'] = get_query_param('ros_package')
    d['ros_launch'] = get_query_param('ros_launch')
    d['ros_args'] = get_query_param('ros_args', "")
    d['latency'] = get_query_param('latency')
    d['timeout'] = get_query_param('timeout')
    d['uplink_data_cap'] = get_query_param('uplink_data_cap')
    d['downlink_data_cap'] = get_query_param('downlink_data_cap')
    d["local_start"] = get_query_param("local_start")
    d["local_stop"] = get_query_param("local_stop")
    d["vrc_id"] = get_query_param("vrc_id")
    d["vrc_num"] = get_query_param("vrc_num")
    return d


def process_http_post(role, constellation, task_id):
    if role == "user":
        refuse_authorization()
    d = get_task_params(constellation, 'create_task')
    log("Create (post) tasks: %s" % d)

    s = json.dumps(d)
    r.publish('cloudsim_cmds', s)
    print('Content-type: application/json')
    print("\n")
    print("%s" % s)


def process_http_put(role, constellation, task_id):
    if role == "user":
        refuse_authorization()
    d = get_task_params(constellation, 'update_task')

    log("Update (put) tasks: %s" % d)

    s = json.dumps(d)
    r.publish('cloudsim_cmds', s)
    print('Content-type: application/json')
    print("\n")
    print("%s" % s)


def get_task(constellation_name, task_id):

    try:
        key = 'cloudsim/' + constellation_name
        s = r.get(key)
        c = json.loads(s)
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


def get_query_param(param, default=""):
    qs = os.environ['QUERY_STRING']
    params = urlparse.parse_qs(qs)
    p = None
    try:
        p = params[param][0]
    except:
        p = default
    return p


email = authorize()
udb = UserDatabase()
role = udb.get_role(email)

method = os.environ['REQUEST_METHOD']
constellation, task_id = parse_path()

if method == 'GET':
    process_http_get(role, constellation, task_id)
elif method == 'DELETE':
    process_http_delete(role, constellation, task_id)
elif method == 'PUT':
    process_http_put(role, constellation, task_id)
elif method == 'POST':
    process_http_post(role, constellation, task_id)
