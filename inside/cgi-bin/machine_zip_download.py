#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import cgi
import cgitb
import os
import sys
import redis
from common.web import print_http_header
from common.machine_configuration import get_constellation_data

cgitb.enable()

from common import  authorize

red = redis.Redis()

def get_machine_zip_key(email, constellation_name, machine_name):
    constellation = get_constellation_data(email, constellation_name)
    directory = constellation['constellation_directory']
    path = os.path.join(directory,machine_name,machine_name + ".zip" )
    return path

def log(msg):
    red.publish("machine_zip_download", "[machine_zip_download.py] " + msg)

def download(filename):
    short_name = os.path.split(filename)[1]
    
    # print ("\nStatus:200\n)
    
    print ("Content-Type: application/octet-stream")
    print ("Content-Disposition: attachment; filename=%s" % short_name)
    print ("")

    f = open(filename, 'rb')
    while True:
        data = f.read(4096)
        sys.stdout.write(data)
        if not data:
            break

email = authorize()

form = cgi.FieldStorage()
constellation_name = form.getfirst('constellation')
machine_name = form.getfirst('machine')

try:
    filename = get_machine_zip_key(email, constellation_name, machine_name)

    log("constellation_name: %s" % constellation_name)
    log("machine_name: %s" % machine_name)
    log(filename)
    
    if os.path.exists(filename):
        download(filename)
    else:
      
        print ("Status: 404 Not Found")
        print ("Content-Type: text/html\n\n")
        print ("<h1>404 File not found!</h1>" )
        print("<br>" + filename + "")
        
except Exception, e:   
    print_http_header()
    print ("<title>Access Denied</title>")
    print ("<h1>Access Denied: " + str(e) +"</h1>")
    