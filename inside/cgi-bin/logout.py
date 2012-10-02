#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi, cgitb
cgitb.enable()
import Cookie
import os

import common

out_cookies = Cookie.SmartCookie()
out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''
out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = '/cloudsim/inside/cgi-bin/'
print(out_cookies)
print("""Content-type: text/html

<h1>Goodbye</h1>
<a href="/cloudsim/login.html">login</a>
<p>
<a href="http://www.google.com/accounts/logout">Google Logout</a>

""")