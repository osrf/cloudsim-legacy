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

# Are we using basic auth?
auth_type, email = common.web.get_auth_type()

if auth_type == 'OpenID':
    # Get form and cookie data
    form = cgi.FieldStorage()
    email = form.getfirst(EMAIL_VARNAME)
    in_cookies = Cookie.Cookie()
    in_cookies.load(os.environ[common.HTTP_COOKIE])
    openid_session = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value
    sdb = common.SessionDatabase()
    sdb.load()

    if not email:
        if openid_session in sdb.db:
            email = sdb.db[openid_session]

# Check email 
udb = common.UserDatabase()
users = udb.get_users()

# Force email to lower case for comparison to users list, which we
# lower-cased when loading.
if email:
    email = email.lower()

if email not in users:

    # print ("openid_session %s" % openid_session)
    if email:
        common.print_http_header()
        print("Access Denied ... '%s' not in users<br>" % (email))
        sys.exit(0)
    elif auth_type == 'OpenID':
        out_cookies = Cookie.SmartCookie()
        out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''
        out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = '/cloudsim/inside/cgi-bin/'
        print(out_cookies)
        common.print_http_header()
        print("""
        Your open session ID is not associated with a user. Please login again<br>
        <a href="/cloudsim/index.html">login</a>
        """)
        sys.exit(0)

# Save session ID and email to our own database
if auth_type == 'OpenID':
    sdb.db[openid_session] = email
    sdb.save()

# redirect to the console now
common.print_http_header()
print ('<meta http-equiv="refresh" content="0; url=/cloudsim/inside/cgi-bin/console">')

