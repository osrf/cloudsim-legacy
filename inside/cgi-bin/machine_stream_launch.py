#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import sys
import os
import time
import cgi
import cgitb

from common import tail, MachineDb

cgitb.enable()
 

from common import authorize, print_http_header
cgitb.enable()

VIEW_AS_HTML = False


email = authorize()

form = cgi.FieldStorage()
machine_name = form.getfirst('machine_name')

if form.has_key('html'):
    if form.getfirst('html') == 'true':
        VIEW_AS_HTML = True
    
    
if VIEW_AS_HTML:
    print_http_header()
    
    print("<h1>Form</h1>")
    for k in form.keys():
        v = form.getfirst(k)
        print("%s = %s<p>" % (k, v))
    print("<h1>machine config %s</h1>" % machine_config_id)
    print("<h1>events</h1>")
else:
    print ("Content-Type: text/event-stream")
    print ("Expires: Fri, 01 Jan 1990 00:00:00 GMT")
    print ("Cache-Control: no-cache, no-store, max-age=0, must-revalidate")
    print ("Pragma: no-cache")
    print ("Connection: close")            
    print
    print
    

def event(name,data,log = None):
    print("event: %s" % name)
    print("data: %s\n" % data )
    sys.stdout.flush()
    if log:
        log.write("event: %s" % event)
        log.write("\n")
        log.write("data: %s\n" % data )
        log.write("\n")




mdb = MachineDb(email)
launch_log_fname = mdb.get_launch_log_fname(machine_name)
event("action", "{log:'%s'}" % launch_log_fname)
tail(launch_log_fname)


    
#for i in range(5):
#    name = "action"
#    data = "{count : %s, name:'%s'}" % (i, machine_name)
#    event(name, data)
#    if VIEW_AS_HTML:
#        print("<p>")
#        
#    time.sleep(0.1)
#
#event("machine", "%s" % machine_name)    
    
event("done","{}")

