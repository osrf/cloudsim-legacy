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
domain = email.split('@')[1]

common.print_http_header()
print("<h1>CloudSim console for %s</h1>"%(domain))
print("<p>Your currently running machines are listed below.  Click on one to see details on how to connect to it.  Or <a href=\"/cloudsim/inside/cgi-bin/machine_launch.py\">launch a new machine</a>.</p>")

print("<h3>Running machines:</h3>")
#machine_ids = ['123', '456', '789']
(machine_ids, incomplete_machine_ids) = common.list_machines(email)
print("<p><ul>")
for m in machine_ids:
    print("<li><a href=\"/cloudsim/inside/cgi-bin/machine_detail.py?%s=%s\">%s</a>"%(common.MACHINE_ID_VARNAME,m.name,m.name))
for m in incomplete_machine_ids:
    print("<li>%s (provisioning now...) <a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">[%s]</a>"%(m.name,common.MACHINE_ID_VARNAME, m.name, common.ACTION_VARNAME, 'terminate', 'Terminate'))
if not machine_ids and not incomplete_machine_ids:
    print("<li>(none)")
print("</ul></p>")
common.print_footer()
