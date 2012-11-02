#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
cgitb.enable()

from common import  authorize, MachineDb

email = authorize()

form = cgi.FieldStorage()
machine_name = form.getfirst('machine')

print "Content-Type: application/octet-stream"
print "Content-Disposition: attachment; filename=jstock.exe"
print

mdb = MachineDb(email)
filename = mdb.get_zip_fname(machine_name)

f = open(filename, 'rb')
while True:
    data = f.read(4096)
    sys.stdout.write(data)
    if not data:
        break