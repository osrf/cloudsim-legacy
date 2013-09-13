#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import os
import cgitb
import Cookie


cgitb.enable()

import common

auth_type, email = common.web.get_auth_type()

if auth_type == 'Basic':
    print('Status: 401 Authorization Required')
elif auth_type == 'OpenID':
    out_cookies = Cookie.SmartCookie()
    out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''

    partial_path = '/cloudsim/inside/cgi-bin/'
    out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = partial_path
    print(out_cookies)

print("""Content-type: text/html

<h1>Goodbye</h1>
<a href="/cloudsim/login.html">login</a>
""")
if auth_type == 'OpenID':
  print("""<p>
<a href="http://www.google.com/accounts/logout">Google Logout</a>

""")
