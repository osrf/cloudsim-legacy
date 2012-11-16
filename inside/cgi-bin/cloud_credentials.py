#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import os
import cgi
import cgitb
import json

import redis
from common import  authorize, UserDatabase, CloudCredentials



cgitb.enable()


email = authorize()
form = cgi.FieldStorage()
method = os.environ['REQUEST_METHOD']


red = redis.Redis()


access = None
secret_access = None


try:
    aws_access_key_id = form.getfirst("access_key", None)
    aws_secret_access_key = form.getfirst("secret_access_key", None)
except Exception, e:
    # bug? cgi.FieldStorage() does not work for http delete
    q_string= os.environ['QUERY_STRING']
    red.publish("cloudsim_log", "cloud_credentials.py error '%s' query string %s" % (e,q_string) )

red.publish("cloudsim_log", "cloud_credentials.py [%s] (%s) (%s)" % (method, aws_access_key_id, aws_secret_access_key ) )

db = UserDatabase()

r = {}
r['success'] = False

    
print('Content-type: application/json')
print("\n")

if method == 'POST':
    red.publish("cloudsim_admin", "new credentials")
    cloud = CloudCredentials(aws_access_key_id, aws_secret_access_key)
    if cloud.validate():
        cloud.save()
        r['success'] = True
    # DO it!
    
if method == 'DELETE':
    # not supported
    pass

if method == 'GET':
    # not authorized?
    pass

jr = json.dumps(r)
print(r)
