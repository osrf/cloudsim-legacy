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
    print("Error: Machine not found.  Perhaps it is still being provisioned.  Check status at the <a href=\"/cloudsim/inside/cgi-bin/console.py\">console</a>.<br>")
else:
    machine = matches[0]
    aws_state, aws_state_info = machine.get_aws_status()
    ping, ping_err = machine.ping()
    ssh, ssh_err = machine.test_ssh()
    x, x_err = machine.test_X()
    gz, gz_err = machine.test_gazebo()
#    aws_state, aws_state_info = (None, None)
#    ping, ping_err = (None, None)
#    ssh, ssh_err = (None, None)
#    x, x_err = (None, None)
#    gz, gz_err = (None, None)
    if test:
        print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'start', 'Start'))
        print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'stop', 'Stop'))
    print("<a href=\"/cloudsim/inside/cgi-bin/gazebo_launch.py?%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, 'Configure/launch Gazebo'))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'reboot', 'Reboot'))
    print("<a href=\"/cloudsim/inside/cgi-bin/machine_action.py?%s=%s&%s=%s\">%s</a><br>"%(common.MACHINE_ID_VARNAME, machine_id, common.ACTION_VARNAME, 'terminate', 'Terminate'))
    print("<ul>")
    
    
    print("<li><b>To connect via <a href='http://openvpn.net/index.php/download.html'>OpenVPN</a>:</b><ol><li>Download these files: <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=openvpn_key\">[key]</a> <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=openvpn_config\">[config]</a>. <li> In a terminal, go to the directory containing those files. <li> Execute the following command: "%(machine_id, machine_id))
    print("<pre>sudo openvpn --config openvpn-%s.config</pre></ol>"%(machine_id))
    print("<li><b>To login via SSH</b>:<ol><li>Download this file: <a href=\"/cloudsim/inside/cgi-bin/machine_download.py?machine_id=%s&attrib=ssh_key\">[key]</a>.<li>In a terminal, go to the directory containing that file.<li>Execute the following commands:"%(machine_id))
    print("<pre>chmod 600 ssh_key-%s.pem\nssh -i ssh_key-%s.pem %s@%s</pre></ol>"%(machine_id, machine_id, machine.username, machine.hostname))

    
    print("""
          <li><b>To connect via ROS:</li><p> 
              <ol>
                  <li>Connect via OpenVPN (see above).
                  <li>Download this file: [ros.sh]
                  <li>In a terminal, go to the directory containing that file.
                  <li>Execute the following command:
                  <pre>. ros.sh</pre>
              </ol>
               
          """)
    
    print("<li><b>Machine status:</b><ul>")
    print("<li>State: %s"%('<font color=green>%s</font>'%(aws_state_info) if aws_state else '<font color=red>ERROR</font> (%s)'%(aws_state_info)))
    print("<li>Ping: %s"%('<font color=green>OK</font>' if ping else '<font color=red>ERROR</font> (%s)'%ping_err))
    print("<li>SSH: %s"%('<font color=green>OK</font>' if ssh else '<font color=red>ERROR</font> (%s)'%ssh_err))
    print("<li>X: %s"%('<font color=green>OK</font>' if x else '<font color=red>ERROR</font> (%s)'%x_err))
    print("<li>Gazebo: %s"%('<font color=green>OK</font>' if gz else '<font color=red>ERROR</font> (%s)'%gz_err))
    print("</ul>")
    #print("<li>IP Address / Hostname: <pre>%s</pre>"%(machine.hostname))
    #print("<li>AWS ID: <pre>%s</pre>"%(machine.aws_id))
    #print("<li>Boto config file: <pre>%s</pre>"%(machine.botofile))
    print("</ul>")

common.print_footer()
