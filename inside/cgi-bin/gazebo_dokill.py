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
    print("Error: machine not found.  Perhaps the machine is still being provisioned.<br>")
else:
    machine = matches[0]
    cmd = ['killall', '-INT', 'roslaunch']
    print("<p>Running the following command: <pre>%s</pre></p>"%(cgi.escape(' '.join(cmd))))
    ret, err = machine.ssh(cmd, args=['-f'])
    # TODO: Differentiate between success and failure, and make message better.
    if ret:
        print("<p>Success.")
    else:
        print("<p>Error: <pre>%s</pre>"%(err))
    print("Return to <a href=\"/cloudsim/inside/cgi-bin/machine_detail.py?%s=%s\">machine details</a>.</p>"%(common.MACHINE_ID_VARNAME, machine_id))

common.print_footer()
