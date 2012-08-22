#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

form = cgi.FieldStorage()
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)
action = form.getfirst(common.ACTION_VARNAME)

common.print_http_header()
print("<title>Reboot machine %s</title>"%(machine_id))
print("Are you sure that you want to %s this machine?<br>"%(action))
print("<form action=\"/cloudsim/inside/cgi-bin/machine_doaction.py\" method=\"GET\">")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.ACTION_VARNAME, action))
print("<input type=\"submit\" value=\"Yes\"/>")
print("</form")
common.print_footer()
