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

d ={}

try:
    d['command'] = form.getfirst('command')
    d['username'] = email
    d['constellation'] = form.getfirst('constellation')
    d['machine'] = form.getfirst('machine')
    
    if d['command'] == 'update_tc':
        d['targetPacketLatency'] = form.getfirst('targetPacketLatency')
    else:
        print ('tc_cmd.py Incorrect command (%s)' % (d['command']))
except Exception, e:
    print ("Error processing traffic shaping commands [%s]" % d)   
        
s = dumps(d)

redis_client = redis.Redis()
redis_client.publish('tc_cmds', d['command'])

redis_client.publish('cloudsim_cmds', s)

print('Content-type: application/json')
print("\n")
print(s)

