#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import sys
import os
import Cookie
import cgi
import common

import cgitb
cgitb.enable()

EMAIL_VARNAME = 'openid.ext1.value.email'

# Get form and cookie data
form = cgi.FieldStorage()
email = form.getfirst(EMAIL_VARNAME)
in_cookies = Cookie.Cookie()
in_cookies.load(os.environ[common.HTTP_COOKIE])
openid_session = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value

sdb = common.SessionDatabase()
sdb.load()

# Check email 
udb = common.UserDatabase()
users = udb.get_users()

if not email:
    if openid_session in sdb.db:
        email = sdb.db[openid_session]
        


if email not in users:
    
    # print ("openid_session %s" % openid_session)
    if email:
        common.print_http_header()
        print("Access Denied ... '%s' not in users<br>" % (email))
        sys.exit(0)
    else:
        
        out_cookies = Cookie.SmartCookie()
        out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''
        out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = '/cloudsim/inside/cgi-bin/'
        print(out_cookies)
        common.print_http_header()
        print("""
        Your open session ID is not associated with a user. Please login again<br>
        <a href="/cloudsim/login.html">login</a>
        """)
        sys.exit(0)



# Save session ID and email to our own database

sdb.db[openid_session] = email
sdb.save()
common.print_http_header()

version_info = common.get_cloudsim_version_txt()

page = """
<!DOCTYPE html>
<html>
<head>
<link href="/js/layout.css" rel="stylesheet" type="text/css">
</head>
<body>
<img src="/js/images/osrf.png" width="400px"/>
<div>

<h1>CloudSim %s</h1>

</div>

<div style="padding: 10px; margin-bottom:20px; margin-top:20px;" more="border-radius: 15px; border: 1px solid black; "> 
<pre>

</pre>
</div>

<a href="/cloudsim/inside/cgi-bin/console">Console</a><br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<a href="https://bitbucket.org/osrf/cloudsim">Source</a>
</body>
</html>
""" % version_info
print(page)
#print("Location: /cloudsim/inside/cgi-bin/console\n")

