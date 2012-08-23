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
attrib = form.getfirst(common.ATTRIB_VARNAME)

email = common.session_id_to_email()
machines = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
if not matches:
    common.print_http_header()
    print("Error: machine not found.<br>")
    common.print_footer()
else:
    machine = matches[0]
    if attrib == 'ssh_key':
        filename = 'ssh_key-%s.pem'%(machine_id)
        common.print_http_filedownload_header(filename)
        print(machine.ssh_key)
    elif attrib == 'openvpn_key':
        filename = 'openvpn-%s.key'%(machine_id)
        common.print_http_filedownload_header(filename)
        print(machine.openvpn_key)
    elif attrib == 'openvpn_config':
        filename = 'openvpn-%s.config'%(machine_id)
        common.print_http_filedownload_header(filename)
        print(machine.openvpn_config)
    else:
        common.print_http_header()
        err = "Unknown attribute \"%s\""%(attrib)
        print("Error: <pre>%s</pre>"%(err))
        common.print_footer()

