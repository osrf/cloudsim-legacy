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

form = cgi.FieldStorage()
instance_type = form.getfirst('instance_type')
image_id = form.getfirst('image_id')
zone = form.getfirst('zone')

email = common.session_id_to_email()
domain = email.split('@')[1]

common.print_http_header()

if zone == 'useast':
    botofile = common.BOTO_CONFIG_FILE_USEAST
elif zone == 'uswest-ca':
    botofile = common.BOTO_CONFIG_FILE_USWEST_CA
else:
    print("Error: unknown zone \"%s\"."%(zone))
    sys.exit(0)

import create_ec2_instance
module_dir = os.path.dirname(create_ec2_instance.__file__)
script = """#!/usr/bin/env python
import sys
sys.path.append('%s')
import create_ec2_instance
create_ec2_instance.create_ec2_instance('%s', '%s', instance_type='%s', image_id='%s')"""%(module_dir, botofile, os.path.join(common.MACHINES_DIR, domain), instance_type, image_id)
common.start_background_task(script)

print("Machine launched.  It may be up to 15 minutes before it's available. Check status at the <a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a>.")

common.print_footer()
