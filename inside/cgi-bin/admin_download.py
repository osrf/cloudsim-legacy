#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import cgitb
import os
import sys
cgitb.enable()

from common import  authorize


TEAM_LOGIN_SSH_FNAME = '/var/www/cloudsim_ssh.zip'


email = authorize("admin")

#form = cgi.FieldStorage()
#filename = form.getfirst('file')

short_name = os.path.split(TEAM_LOGIN_SSH_FNAME)[1]
print ("Content-Type: application/octet-stream")
print ("Content-Disposition: attachment; filename=%s" % short_name)
print ("")

f = open(TEAM_LOGIN_SSH_FNAME, 'rb')
while True:
    data = f.read(4096)
    sys.stdout.write(data)
    if not data:
        break
