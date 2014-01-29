#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import redis
from json import dumps
import cgi
import cgitb
from common import authorize

cgitb.enable()
email = authorize()
form = cgi.FieldStorage()

d = {}
d['command'] = form.getfirst('command')
d['username'] = email


if d['command'] == 'start_task':
    d['constellation'] = form.getfirst('constellation')
    d['task_id'] = form.getfirst('task_id')

if d['command'] == 'stop_task':
    d['constellation'] = form.getfirst('constellation')
    # d['task_id'] = form.getfirst('task_id')

if d['command'] in ['reset_tasks',
                    'start_gzweb',
                    'stop_gzweb',
                    'start_cloudsim_notebook',
                    'stop_cloudsim_notebook']:
    d['constellation'] = form.getfirst('constellation')

s = dumps(d)
redis_client = redis.Redis()
redis_client.publish('cloudsim_cmds', s)

print('Content-type: application/json')
print("\n")
print(s)