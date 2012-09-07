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
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)

email = common.session_id_to_email()
(machines, incompletes) = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
if not matches:
    print("Error: machine not found.  Perhaps the machine isn't done being created yet.<br>")
else:
    machine = matches[0]
    cmd = ['\"nohup killall -INT roslaunch >/dev/null 2>/dev/null </dev/null &\"']
    print("<p>Running the following command: <pre>%s</pre></p>"%(cgi.escape(' '.join(cmd))))
    ret, err = machine.ssh(cmd, args=['-f'])
    if ret:
        print("<p>Success.")
    else:
        print("<p>Error: <pre>%s</pre>"%(err))
    print("Proceed to the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.</p>")

common.print_footer()
