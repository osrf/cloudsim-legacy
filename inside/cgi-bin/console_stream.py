#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import sys
import os
import time
import cgi
import cgitb

import redis

from json import loads

cgitb.enable()
 

from common import authorize, print_http_header
cgitb.enable()

VIEW_AS_HTML = False

email = authorize()
domain = email.split('@')[1]

form = cgi.FieldStorage()
if form.has_key('html'):
    VIEW_AS_HTML = True
    print("Content-Type: text/html")
    print("\n")
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
#    sys.stdout.flush()
#    # time.sleep(0.05)    
#    
#exit(0)

red = redis.Redis()
pubsub = red.pubsub()


pubsub.subscribe([domain])

for msg in pubsub.listen():
    try:
        data = msg['data']
        print("event: cloudsim")
        print("data: %s\n\n" % data)
        sys.stdout.flush() 
    except:
        pass


if VIEW_AS_HTML:
    print ("</pre></html>")     