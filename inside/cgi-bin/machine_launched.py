#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys
import os

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

common.print_http_header()

print("<p>Machine launched.  It may be up to 15 minutes before it's available. Check status at the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.</p>")

common.print_footer()
