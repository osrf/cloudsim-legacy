#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys
import time

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

form = cgi.FieldStorage()
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)
test = form.getfirst('test')
if test:
    test = int(test)

common.print_http_header()
print("<title>Detail for machine %s</title>"%(machine_id))
print("<h1>Detail for machine %s</h1>"%(machine_id))

email = common.session_id_to_email()
machines = common.list_machines(email)[0]
matches = [m for m in machines if m.name == machine_id]
if not matches:
    print("Error: machine not found.<br>")
else:
    machine = matches[0]
    aws_state, aws_state_info = machine.get_aws_status()
    ping, ping_err = machine.ping()
    ssh, ssh_err = machine.test_ssh()
    x, x_err = machine.test_X()
    gz, gz_err = machine.test_gazebo()
    if test:
        print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'start', 'Start'))
        print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'stop', 'Stop'))
    print("<a href=\"/cloudsim/inside/cgi-bin/gazebo_launch.py?%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, 'Configure/launch Gazebo'))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'reboot', 'Reboot'))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'terminate', 'Terminate'))
    print("<ul>")
    print("<li>Status:<ul>")
    print("<li>State: %s"%('<font color=green>%s</font>'%(aws_state_info) if aws_state else '<font color=red>ERROR</font> (%s)'%(aws_state_info)))
    print("<li>Ping: %s"%('<font color=green>OK</font>' if ping else '<font color=red>ERROR</font> (%s)'%ping_err))
    print("<li>SSH: %s"%('<font color=green>OK</font>' if ssh else '<font color=red>ERROR</font> (%s)'%ssh_err))
    print("<li>X: %s"%('<font color=green>OK</font>' if x else '<font color=red>ERROR</font> (%s)'%x_err))
    print("<li>Gazebo: %s"%('<font color=green>OK</font>' if gz else '<font color=red>ERROR</font> (%s)'%gz_err))
    print("</ul>")
    print("<li>IP Address / Hostname: <pre>%s</pre>"%(machine.hostname))
    print("<li>SSH (username: <tt>%s</tt>): <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=ssh_key\">[Download key]</a>"%(machine.username, machine_id))
    print("<pre>chmod 600 ssh_key-%s.pem\nssh -i ssh_key-%s.pem %s@%s</pre>"%(machine_id, machine_id, machine.username, machine.hostname))
    print("<li>OpenVPN: <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=openvpn_key\">[Download key]</a> <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=openvpn_config\">[Download config]</a>"%(machine_id, machine_id))
    print("<pre>sudo openvpn --config openvpn-%s.config</pre>"%(machine_id))
    print("<li>AWS ID: <pre>%s</pre>"%(machine.aws_id))
    print("<li>Boto config file: <pre>%s</pre>"%(machine.botofile))
    print("</ul>")

common.print_footer()
