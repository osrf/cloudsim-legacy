#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgitb
import Cookie


cgitb.enable()

import common

out_cookies = Cookie.SmartCookie()
out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''

partial_path = '/cloudsim/inside/cgi-bin/'
out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = partial_path
print(out_cookies)
print("""Content-type: text/html

<h1>Goodbye</h1>
<a href="/cloudsim/login.html">login</a>
<p>
<a href="http://www.google.com/accounts/logout">Google Logout</a>

""")
