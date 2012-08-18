#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi, cgitb
cgitb.enable()
import Cookie
import os

import common

out_cookies = Cookie.Cookie()
out_cookies[common.CLOUDSIM_SESSION_COOKIE_NAME] = ''
out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''
print(out_cookies)
print("Content-type: text/html\n")
print("<h1>Goodbye</h1>")
print("<a href=\"/cloudsim/login.html\">login</a>")

