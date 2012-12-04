#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import sys

import redis
from json import dumps
import cgi
import cgitb


cgitb.enable()


from common import authorize

email = authorize()



form = cgi.FieldStorage()


d ={}
d['command'] = form.getfirst('command')
d['username'] = email



if d['command'] == 'start_simulator':
    d['machine'] = form.getfirst('machine')
    d['package_name'] = form.getfirst('package')
    d['launch_file_name'] = form.getfirst('launch_file_name')
    d['launch_args'] = form.getfirst('launch_args', default = '')

if d['command'] == 'stop_simulator':
    d['machine'] = form.getfirst('machine')

str = dumps(d)

redis_client = redis.Redis()
redis_client.publish('cloudsim_cmds', str)

print('Content-type: application/json')
print("\n")
print(str)
