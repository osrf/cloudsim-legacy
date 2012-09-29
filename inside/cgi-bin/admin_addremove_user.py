#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import shutil
import cgitb
cgitb.enable()
import sys

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

common.print_http_header()

form = cgi.FieldStorage()

d = {}

d['action'] = form.getfirst('action') # common.MACHINE_ID_VARNAME
d['user'] = form.getfirst('email') # common.MACHINE_ID_VARNAME
d['keys'] = form.keys()

udb = common.UserDatabase()

template = """
<h1>CloudSim admin</h1>
<h2>UNKNOWN ACTION!</h2>
keys = {keys}<br>
action = {action}<br>
email = {user}<br>
""" 



if d['action'] == "add":
    udb.add_user(d['user'])
    template = """
<h1>CloudSim admin</h1>
<h2>User {user} added succesfully</h2>
<a href="/cloudsim/inside/cgi-bin/admin.py">Return</a><br>
""" 

if d['action'] == "remove":
    udb.remove_user(d['user'])
    template = """
<h1>CloudSim admin</h1>
<h2>User {user} removed</h2>
<a href="/cloudsim/inside/cgi-bin/admin.py">Return</a><br>
""" 
    


page = template.format(**d)
print(page)

common.print_footer()