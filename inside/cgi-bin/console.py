#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import Cookie
import os
import sys

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

email = common.session_id_to_email()

common.print_http_header()
print("<h1>CloudSim Console</h1>")

print("<h2>Running machines</h2>")
#machine_ids = ['123', '456', '789']
machine_ids = common.list_machines(email)
print("<p><ul>")
for m in machine_ids:
    print("<li><a href=\"/cloudsim/inside/cgi-bin/machine_detail.py?%s=%s\">%s</a> <a href=\"/cloudsim/inside/cgi-bin/machine_kill.py?%s=%s\">[terminate]</a>"%(common.MACHINE_ID_VARNAME,m.name,m.name,common.MACHINE_ID_VARNAME,m.name))
print("</ul></p>")

print("<p><a href=\"/cloudsim/inside/cgi-bin/machine_launch.py\">Launch a new machine</a></p>")

common.print_footer()
