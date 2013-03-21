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
    r.publish('constellations', msg)

def _domain(email):
    domain = email.split('@')[1]
    return domain


def clean_constellation_data(constellation):
    """
    Remove data from the constellation to avoid cheating in the VRC
    """
    constellation.pop("constellation_directory")
    censored_tasks = []
    for task in constellation.tasks:
        t = {'task_title':task['task_title'], 
             'task_state': task['task_state'],
             'task_id' : task['task_id']}
        censored_tasks.append(t)
        

def get_constellation(email, constellation_name):

    try:
        key = 'cloudsim/' + constellation_name
       
        s = r.get(key)
        c = json.loads(s)
        log("c %s" % c)
        
        domain = _domain(c['username'])
        authorised_domain = _domain(email)
        
        x = None
        if domain == authorised_domain:
            x = c
        constellation = clean_constellation_data(x)
        return constellation
    
    except:
        return None

def list_constellations(email):
    constellations = []
    for key in r.keys():
        
        toks = key.split('cloudsim/')
        if len(toks) == 2:
            constellation_name = toks[1]
            c = get_constellation(email, constellation_name)
            if c:
                log(constellation_name)
                constellations.append(c )
    
    
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
    log("Constellations")
    try:    
        
        constellation = get_constellation_from_path()
        
        
        if len(constellation) > 0:
            domain = _domain(email)
            key = "cloudsim/"+ constellation
            s = r.get(key)
        else:
            log("listing all constellations")
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
    
  
if method == 'POST':
    d = {}
    d['username'] = email
    d['command'] = 'launch'
    d['configuration'] = get_query_param('configuration')
    
s = json.dumps(d)
r.publish('cloudsim_cmds', s)
print("%s" % s)