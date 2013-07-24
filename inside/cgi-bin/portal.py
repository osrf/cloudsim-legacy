#!/usr/bin/env python

from __future__ import print_function

import os
import cgitb
import json

import redis
from common import  authorize, get_cloudsim_config
import urlparse


cgitb.enable()


def read_portal():
    cfg = get_cloudsim_config()
    if os.path.exists(cfg['cloudsim_portal_json_path']):
        with open(cfg['cloudsim_portal_json_path'], 'r') as f:
            d = json.loads(f.read())
            return d
    return {"hostname": "vrcportal-test.osrfoundation.org", "user": "ubuntu",
             "event": "practice",
             "team": "T001",
             "upload_dir": "/tmp",
             "final_destination_dir": "/vrc_logs/end_incoming",
             "live_destination": "/vrc_logs/live_incoming"}


def write_portal(d):
    cfg = get_cloudsim_config()
    if os.path.exists(cfg['cloudsim_portal_json_path']):
        with open(cfg['cloudsim_portal_json_path'], 'w') as f:
            j = json.dumps(d)
            f.write(j)


def log(msg):
    red = redis.Redis()
    s = "portal.py > %s" % msg
    red.publish("portal", s)


email = authorize("admin")
method = os.environ['REQUEST_METHOD']
q_string = os.environ['QUERY_STRING']
log("query string %s" % (q_string))


try:

    q = urlparse.parse_qs(q_string)
    r = {}
    r['success'] = False

    if method == 'PUT':
        # valid = override_creds(r['team'], r['hostname'])
        try:
            team = q['team'][0]
            hostname = q['hostname'][0]
            r['team'] = team
            r['hostname'] = hostname
            portal = read_portal()
            portal['team'] = team
            portal['hostname'] = hostname
            write_portal(portal)
            r['success'] = True
            r['msg'] = 'New portal info: team %s on %s.' % (team, hostname)
        except Exception, e:
            r['msg'] = 'Error setting portal information: %s' % e
    if method == 'POST':
        # not supportedr
        r['msg'] = 'operation not supported'
        pass

    if method == 'DELETE':
        # not supported
        r['msg'] = 'operation not supported'
        pass

    if method == 'GET':
        r = read_portal()

    jr = json.dumps(r)
    log("JSON response %s" % jr)
    print('Content-type: application/json')
    print("\n")
    print(jr)


except Exception, e:
    log(e)
    raise
