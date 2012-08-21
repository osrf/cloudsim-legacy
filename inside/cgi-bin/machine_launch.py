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

common.print_http_header()
print("<title>Launch a new machine</title>")
print("<h1>Launch a new machine</h1>")

print("<form action=\"/cloudsim/inside/cgi-bin/machine_dolaunch.py\" method=\"GET\">")
print("<input type=\"submit\" value=\"Launch\"/>")
print("</form>")


common.print_footer()
