#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys
import os

import common
import create_ec2_instance

if not common.check_auth_and_generate_response():
    sys.exit(0)

email = common.session_id_to_email()

common.print_http_header()
print("<hr>")
print("<pre>")
create_ec2_instance.create_ec2_instance(common.BOTO_CONFIG_FILE,
                                        os.path.join(common.MACHINES_DIR, email)
)
print("</pre>")
print("<hr>")
print("Machine launched.  Proceed to the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.")

common.print_footer()
