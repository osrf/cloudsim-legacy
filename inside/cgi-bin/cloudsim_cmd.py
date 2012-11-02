#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import sys

import redis
from json import dumps
import cgi
import cgitb


cgitb.enable()


from common import ConfigsDb, authorize

email = authorize()



form = cgi.FieldStorage()
  

d ={}
d['command'] = form.getfirst('command')

if d['command'] == 'launch':
    d['configuration'] = form.getfirst('machine_config')

d['username'] = email

str = dumps(d)
#
redis_client = redis.Redis()
redis_client.publish('cloudsim_cmds', str)

print('Content-type: application/json')
print("\n")
print(str)
