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

common.print_http_header()
print("<h1>Console</h1>")

email = common.session_id_to_email()
print("Logged in as: %s"%(email))

print("<hr><a href=\"/cloudsim/inside/cgi-bin/logout.py\">logout</a><br>")
