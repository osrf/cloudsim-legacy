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


aws_access_key_id = None
aws_secret_access_key = None


try:
    aws_access_key_id = form.getfirst("access_key")
    aws_secret_access_key = form.getfirst("secret_access_key")
except Exception, e:
    # bug? cgi.FieldStorage() does not work for http delete
    pass
q_string= os.environ['QUERY_STRING']
red.publish("cloudsim_log", "cloud_credentials.py query string %s" % (q_string) )

red.publish("cloudsim_log", "cloud_credentials.py [%s] (%s) (%s)" % (method, aws_access_key_id, aws_secret_access_key ) )

db = UserDatabase()

r = {}
r['success'] = False
r['msg']="Undefined"
r['aws_access_key_id'] = aws_access_key_id
r['aws_secret_access_key'] = aws_secret_access_key

print('Content-type: application/json')
print("\n")

if method == 'PUT':
    red.publish("cloudsim_admin", "new credentials")
    cloud = CloudCredentials(aws_access_key_id, aws_secret_access_key)
    if cloud.validate():
        cloud.save()
        r['success'] = True
        r['msg'] = 'The credentials have been changed.'
        red.publish("cloudsim_log","yes")
    else:
        r['msg'] = "The credentials are not valid."
        

if method == 'POST':
    # not supported
    pass

if method == 'DELETE':
    # not supported
    pass

if method == 'GET':
    # not authorized?
    pass

jr = json.dumps(r)
print(jr)
