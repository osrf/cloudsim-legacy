#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import sys
import os
import time
import cgi
import cgitb

import redis

from common import MachineDb

cgitb.enable()
 

from common import authorize, print_http_header
cgitb.enable()

VIEW_AS_HTML = False

email = authorize()

form = cgi.FieldStorage()
if form.has_key('html'):
    VIEW_AS_HTML = True
    print_http_header()
    print("<html><h1>Form</h1>")
    for k in form.keys():
        v = form.getfirst(k)
        print("%s = %s<p>" % (k, v))
        print("<h1>events</h1>")
        print ("<pre>")
else:
    print ("Content-Type: text/event-stream")
    print ("Expires: Fri, 01 Jan 1990 00:00:00 GMT")
    print ("Cache-Control: no-cache, no-store, max-age=0, must-revalidate")
    print ("Pragma: no-cache")
    print ("Connection: close")            
    print ("")
    print ("")


#for i in range(100):# ps.listen() 
#    print ("event: cloudsim")
#    data = {}
#    data['type'] = 'action'
#    data['counter'] = i
#    print ("data: %s\n\n" % data)
#    # time.sleep(0.05)    
#    
#exit(0)
    
mdb = MachineDb(email)
machines = mdb.get_machines()
for config in machines:
    machine = mdb.get_machine(config)
    m = machine.test_aws_status()
    print("event: cloudsim")
    print("data:  {'aws_status': '%s', 'machine':'%s' }\n\n" % (m, config ))
    p = machine.ping()
    print("event: cloudsim")
    print("data: {'ping': '%s', 'machine':'%s' \n\n" % (str(p), config  ) )
    x = machine.test_X()
    print("event: cloudsim")
    print("data: {'X_GL': '%s', 'machine':'%s' \n\n" % (str(x), config ) )
    g = machine.test_gazebo()
    print("event: cloudsim")
    print("data: {'sim': '%s', 'machine':'%s' \n\n" % (str(g), config  ) )
        #    
    #    launch_log_fname = mdb.get_launch_log_fname(machine_name)
#         domain = email.split('@')[1]
#         ps = redis.Redis().pubsub()
#         ps.subscribe([domain])
#         

    
if not VIEW_AS_HTML:
    print ("</pre></html>")     