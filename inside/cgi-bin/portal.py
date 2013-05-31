#!/usr/bin/env python

from __future__ import print_function

import os
import cgitb
import json

import redis
from common import  authorize, get_cloudsim_config
import urlparse
from common import SoftLayerCredentials



cgitb.enable()


def override_creds(user, api_key):
    """
    writes new SoftLayer credentials 
    when validation succeeds
    """
    config = get_cloudsim_config()
    path = config['softlayer_path']
    creds = SoftLayerCredentials(user, api_key, path)
    valid = creds.validate()
    if valid:
        creds.save()
    return valid

def log(msg):
    red = redis.Redis()
    s = "cloud_credential_softlayers.py > %s" % msg 
    red.publish("cloud_credentials_softlayer", s)
    

email = authorize("admin")
method = os.environ['REQUEST_METHOD']
q_string= os.environ['QUERY_STRING']
log("query string %s" % (q_string) )


try:
    
    # get the location of the AWS credentials from the cloudsim daemon

    q = urlparse.parse_qs(q_string)

    r = {}
    r['success'] = False
    r['msg']="Undefined"
    r['user'] = q['user'][0] 
    r['api_key'] = q['api_key'][0]
    
    print('Content-type: application/json')
    print("\n")
    
    if method == 'PUT':
        log("new credentials:")
        log("   query %s" % q)
        log("   user %s" %r['user'])
        log("   api_key %s" %r['api_key'])
        valid = True
        
        valid = override_creds(r['user'], r['api_key'])
                               
        
        if valid:
            # save
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
    log("JSON response %s" % jr)

    print(jr)       

    
except Exception, e:
    log(e)
    
    
