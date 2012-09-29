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

aws_access_key_id = form.getfirst('aws_access_key_id') # common.MACHINE_ID_VARNAME
aws_secret_access_key = form.getfirst('aws_secret_access_key') # common.MACHINE_ID_VARNAME

keys = form.keys()
cloud = common.CloudCredentials(aws_access_key_id, aws_secret_access_key)

        
template = """
<h1>CloudSim cloud authentication</h1>
<h2>New credentials entered</h2>

%s

""" 
page = template % (cloud.config_text)



if cloud.validate():
    cloud.save()
    page = """
<h1>CloudSim cloud authentication</h1>
<h2>Success: connection established. The new credentials have been saved</h2>    
<a href="/cloudsim/inside/cgi-bin/admin.py">Return</a><br>
    """
    
else:
    page = """
<h1>CloudSim cloud authentication</h1>
<h2>Could not connect to the cloud. Please enter valid information</h2>
<a href="/cloudsim/inside/cgi-bin/admin.py">Return</a><br>    
    
    """

print(page)

common.print_footer()