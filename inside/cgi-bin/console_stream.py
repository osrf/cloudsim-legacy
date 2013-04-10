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
 

from common import authorize, UserDatabase
cgitb.enable()



def message_loop(channels):
    red = redis.Redis()
    pubsub = red.pubsub()
    pubsub.subscribe(channels)
    
    tick_count = 0
    for msg in pubsub.listen():
        data = msg['data']
        print("event: cloudsim")
        print("data: %s\n\n" % data)
        sys.stdout.flush()
        if msg['channel'] == "cloudsim_tick":
            tick_count +=1
            if tick_count == 10:
                # red.publish("cloudsim_log", "console_stream for user %s DONE" % email )
                return

email = authorize()
udb = UserDatabase()
domain =  udb.get_domain(email)

VIEW_AS_HTML = False

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


channels = [domain, "cloudsim_tick"]
message_loop(channels)


        
        
        
    #except Exception, e :
    #    red.publish("cloudsim_log", "Error in console_stream: %s" % e) 



if VIEW_AS_HTML:
    print ("</pre></html>")     