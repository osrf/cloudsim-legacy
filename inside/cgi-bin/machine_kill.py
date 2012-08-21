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
id = form.getfirst(common.MACHINE_ID_VARNAME)

common.print_http_header()
print("<title>Terminate machine %s</title>"%(id))
print("<h1>Machine %s terminated</h1>"%(id))
print("Termination summary goes here...")
common.print_footer()
