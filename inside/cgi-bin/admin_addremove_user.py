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

action = form.getfirst('action') # common.MACHINE_ID_VARNAME
email = form.getfirst('email') # common.MACHINE_ID_VARNAME

keys = form.keys()

template = """
<h1>CloudSim admin</h1>
<h2>Add / remove users</h2>
keys = %s<br>
action = %s<br>
email = %s<br>
""" 

page = template % (keys, action, email)

print(page)

common.print_footer()