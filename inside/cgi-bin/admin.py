#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import shutil
import cgitb

import sys
 
import common

cgitb.enable()

if not common.check_auth_and_generate_response():
    sys.exit(0)

common.print_http_header()

form = cgi.FieldStorage()

def html_list_from_str_list(users):
    l =['<li>' + u + '</li>' for u in users]
    return '\n'.join(l)
    

page_template = """
<h1>CloudSim admin</h1>

<h2>Cloud provider credentials</h2>
<form action="/cloudsim/inside/cgi-bin/admin_cloud_credentials.py">
    Access key ID<input type="text" name="aws_access_key_id">
    Secret access key<input type="text" name="aws_secret_access_key"><input type="submit" value="override"/>
</form>

<h2>Add / remove users</h2>
<p>These users are authorized to Launch simulation instances</p>
    
    {list_of_users}
<p/>
    
<form action= "/cloudsim/inside/cgi-bin/admin_addremove_user.py" method="GET">
    email<input type="email" name="email"/>
    <input type="radio" name="action" value="add" checked>Add
    <input type="radio" name="action" value="remove">Remove
    <input type="submit" value="go"/>
</form>
"""

db = common.UserDatabase()
users = db.get_users()
htlm_list_of_users = html_list_from_str_list(users)

page = page_template.format(list_of_users = htlm_list_of_users)

print(page)

common.print_footer()

