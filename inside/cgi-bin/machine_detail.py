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

common.print_http_header()
print("<title>Detail for machine %s</title>"%(machine_id))
print("<h1>Detail for machine %s</h1>"%(machine_id))

email = common.session_id_to_email()
machines = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
if not matches:
    print("Error: machine not found.<br>")
else:
    machine = matches[0]
    ping, ping_err = machine.ping()
    ssh, ssh_err = machine.test_ssh()
    x, x_err = machine.test_X()
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_start.py?%s=%s\">Start</a><br>"%(common.MACHINE_ID_VARNAME, machine_id))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_stop.py?%s=%s\">Stop</a><br>"%(common.MACHINE_ID_VARNAME, machine_id))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_reboot.py?%s=%s\">Reboot</a><br>"%(common.MACHINE_ID_VARNAME, machine_id))
    print("<ul>")
    print("<li>Status:<ul>")
    print("<li>Ping: %s"%('<font color=green>OK</font>' if ping else '<font color=red>ERROR</font> (%s)'%ping_err))
    print("<li>SSH: %s"%('<font color=green>OK</font>' if ssh else '<font color=red>ERROR</font> (%s)'%ssh_err))
    print("<li>X: %s"%('<font color=green>OK</font>' if x else '<font color=red>ERROR</font> (%s)'%x_err))
    print("</ul>")
    print("<li>AWS ID: <pre>%s</pre>"%(machine.aws_id))
    print("<li>IP Address / Hostname: <pre>%s</pre>"%(machine.hostname))
    print("<li>SSH Key (username: <tt>%s</tt>): <pre>%s</pre>"%(machine.username, machine.ssh_key))
    print("<li>OpenVPN Static Key: <pre>%s</pre>"%(machine.openvpn_key))
    print("<li>OpenVPN Client Configuration: <pre>%s</pre>"%(machine.openvpn_config))
    print("</ul>")

common.print_footer()
