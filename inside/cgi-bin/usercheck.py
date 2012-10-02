#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import sys
import os
import Cookie
import cgi
import common

# Get form and cookie data
form = cgi.FieldStorage()
email = form.getfirst(common.EMAIL_VARNAME)
in_cookies = Cookie.Cookie()
in_cookies.load(os.environ[common.HTTP_COOKIE])
openid_session = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value

# Check email 
udb = common.UserDatabase()
users = udb.get_users()
if email not in users:
    common.print_http_header()
    print("Access Denied ... '%s' not in %s<p>" % (email, users))
    sys.exit(0)

# Save session ID and email to our own database
sdb = common.SessionDatabase()
sdb.load()
sdb.db[openid_session] = email
sdb.save()

# Set a session cookie with our name.
#out_cookies = Cookie.SmartCookie()
#out_cookies[common.CLOUDSIM_SESSION_COOKIE_NAME] = openid_session
#out_cookies[common.CLOUDSIM_SESSION_COOKIE_NAME]['path'] = '/cloudsim/inside/cgi-bin/'
#print(out_cookies)
print("Location: /cloudsim/inside/cgi-bin/console.py\n")

