#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import os
import cgi
import cgitb
import json

import redis
from common import  authorize
import urllib2
from common import CloudCredentials




def log(msg):
    red = redis.Redis()
    red.publish("cloudsim_log", "cloud_credentials.py > %s" % msg )
    


def parse_query_string(str):
    x = str.replace('&secret_access_key=',' ')
    x2 = x.replace('access_key=', '')
    x3 = urllib2.unquote(x2)
    access, secret =  x3.split(' ')
    log("access='%s' secret='%s'" %(access, secret) )
    return access, secret

    
cgitb.enable()
email = authorize("admin")
method = os.environ['REQUEST_METHOD']
q_string= os.environ['QUERY_STRING']
log("query string %s" % (q_string) )





#try:
#    log("FORMIDABLE")
#    log("FORM keys: %s" % form.keys() )
#    aws_access_key_id = form.getfirst("access_key")
#    aws_secret_access_key = form.getfirst("secret_access_key")
#    
#except Exception, e:
#    log(e)
#    pass



#log("[%s] (%s) (%s)" % (method, aws_access_key_id, aws_secret_access_key ) )
#
#db = UserDatabase()
#
try:    
    aws_access_key_id, aws_secret_access_key = parse_query_string(os.environ['QUERY_STRING'])
    r = {}
    r['success'] = False
    r['msg']="Undefined"
    r['aws_access_key_id'] = aws_access_key_id
    r['aws_secret_access_key'] = aws_secret_access_key
    #
    print('Content-type: application/json')
    print("\n")
    #
    if method == 'PUT':
        log("new credentials")
        cloud = CloudCredentials(aws_access_key_id, aws_secret_access_key)
        
        
        if cloud.validate():
            cloud.save()
            r['success'] = True
            r['msg'] = 'The credentials have been changed.'
            
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
    log(jr)
    print(jr)
    
except Exception, e:
    log(e)
    