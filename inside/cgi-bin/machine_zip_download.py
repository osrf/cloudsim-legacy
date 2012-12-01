#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import cgi
import cgitb
import json
import os
import sys
cgitb.enable()

from common import  authorize, MachineDb


email = authorize()

form = cgi.FieldStorage()
constellation_name = form.getfirst('constellation')
machine_name = form.getfirst('machine')

mdb = MachineDb(email)
filename = mdb.get_zip_fname(constellation_name, machine_name)


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

if os.path.exists(filename):
    download(filename)
else:
    print ("Status: 404 Not Found")
    print ("Content-Type: text/html\n\n")
    print ("<h1>404 File not found!</h1>" )
    
    
