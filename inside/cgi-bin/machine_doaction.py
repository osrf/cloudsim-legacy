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

form = cgi.FieldStorage()
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)
action = form.getfirst(common.ACTION_VARNAME)

common.print_http_header()

email = common.session_id_to_email()
(machines, incompletes) = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
inc_matches = [m for m in incompletes if m.name == machine_id]
if not matches and (not inc_matches or action != 'terminate'):
    print("Error: machine not found.  Perhaps the machine isn't done being created yet.<br>")
else:
    if matches:
        machine = matches[0]
    else:
        machine = inc_matches[0]
    if action == 'start':
        ret, err = machine.start()
    elif action == 'stop':
        ret, err = machine.stop()
    elif action == 'terminate':
        ret, err = machine.terminate()
        # Clean up machine directory, irrespective of 
        # whether termination succeeded.
        try:
            shutil.rmtree(machine.path)
        except Exception as e:
            print("<p><font color=\"red\">Warning:</font>: failed to remove machine directory: <pre>%s</pre></p>"%(e))
    elif action == 'reboot':
        ret, err = machine.reboot()
    else:
        ret = False
        err = "Unknown action \"%s\""%(action)


    if ret:
        print("<p>Success.")
    else:
        print("<p>Error: <pre>%s</pre>"%(err))
    print("Proceed to the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.</p>")

common.print_footer()    
