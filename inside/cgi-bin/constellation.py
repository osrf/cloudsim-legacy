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


def get_constellation_from_path():
    constellation = os.environ['PATH_INFO'].split('/')[1]
    return constellation

def get_query_param(param):
    qs= os.environ['QUERY_STRING']
    params = urlparse.parse_qs(qs)
    p = params[param][0]
    return p

email = authorize()
method = os.environ['REQUEST_METHOD']


print('Content-type: application/json')
print("\n")

if method == 'GET':
    r = redis.Redis()
    try:    
        domain = email.split('@')[1]
        key = domain+"/"+ get_constellation_from_path()
        s = r.get(key)
    except:
        s = "%s" % r.keys()
    print(s)
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
    
  
if method == 'POST':
    d = {}
    d['username'] = email
    d['command'] = 'launch'
    d['configuration'] = get_query_param('configuration')
    
s = json.dumps(d)
redis_client = redis.Redis()
redis_client.publish('cloudsim_cmds', s)