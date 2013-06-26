#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import os
import cgitb
import json

import redis
from common import  authorize
import urlparse
from common import CloudCredentials
from common.constants import get_cloudsim_config

cgitb.enable()


def log(msg):
    red = redis.Redis()
    s = "cloud_credentials.py > %s" % msg
    red.publish("cloud_credentials", s)


email = authorize("admin")
method = os.environ['REQUEST_METHOD']
q_string = os.environ['QUERY_STRING']
log("query string %s" % (q_string))


try:

    # get the location of the AWS credentials from the cloudsim daemon
    config = get_cloudsim_config()
    boto_file = config['boto_path']

    d = urlparse.parse_qs(q_string)

    r = {}
    r['success'] = False
    r['user'] = email
    r['msg'] = "Undefined"
    r['aws_access_key_id'] = d['access_key'][0]
    r['aws_secret_access_key'] = d['secret_access_key'][0]
    r['aws_availablity_zone'] = d['availability_zone'][0]
    #
    print('Content-type: application/json')
    print("\n")

    if method == 'PUT':
        log("new credentials")
        cloud = CloudCredentials(r['aws_access_key_id'],
                                 r['aws_secret_access_key'],
                                 ec2_region_name=r['aws_availablity_zone'],
                                 fname=boto_file)

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
