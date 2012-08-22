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

email = common.session_id_to_email()
machines = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
if not matches:
    print("Error: machine not found.<br>")
else:
    machine = matches[0]
    if action == 'start':
        ret, err = machine.start()
    elif action == 'stop':
        ret, err = machine.stop()
    elif action == 'reboot':
        ret, err = machine.reboot()
    else:
        ret = False
        err = "Unknown action \"%s\""%(action)

    if ret:
        print("Success.  Proceed to the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.")
    else:
        print("Error: <pre>%s</pre>"%(err))

common.print_footer()    
