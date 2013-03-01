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

def _domain(email):
    domain = email.split('@')[1]
    return domain

def get_constellation_list(email):
    constellations = []
    domain = _domain(email)
    for k in r.keys():
        # from 'osrfoundation.org/cx45634' to 'cx45634'
        l = k.split(domain+"/")
        if len(l) == 2:
            constellations.append(l[1] )
    return constellations
         


def get_constellation_from_path():
    try:
        constellation = os.environ['PATH_INFO'].split('/')[1]
        return constellation
    except:
        return ""


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
    s = None

    try:    
        
        constellation = get_constellation_from_path()
        
        if len(constellation) > 0:
            domain = _domain(email)
            key = "cloudsim/"+domain+"/"+ constellation
            s = r.get(key)
        else:
            s = get_constellation_list(email) 
           
            
    except Exception, e:
        s = "%s" % e
   
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