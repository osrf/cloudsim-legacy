#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import os
import cgi
import cgitb
import json

import redis
from common import  authorize, UserDatabase


cgitb.enable()


email = authorize("admin")
form = cgi.FieldStorage()
method = os.environ['REQUEST_METHOD']
q_string= os.environ['QUERY_STRING']

red = redis.Redis()


user_name = None

red.publish("cloudsim_log", "query string %s" % q_string)
try:
    user_name = form.getfirst("user", None)
except Exception, e:
    # bug? cgi.FieldStorage() does not work for http delete
    user_name = q_string.split('user=')[1]
    
    
red.publish("cloudsim_log", "user.py [%s] '%s'" % (method, user_name) )

db = UserDatabase()

user = {}
user['name']   = user_name
user['role']  = 'admin'
user['type'] = 'admin'
 

    
print('Content-type: application/json')
print("\n")

if method == 'POST':
    role = form.getfirst("role", None)
    red.publish("cloudsim_log","role is %s" % role)
    db.add_user(user_name, role)
    user['action'] = "added"
        
if method == 'DELETE':
    db.remove_user(user_name)
    user['action'] = "deleted"

if method == 'GET':
    user['action'] = "read"
    
juser = json.dumps(user)
red.publish("cloudsim_admin", juser)
print(juser)

