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
print("""Content-type: text/html""")
page = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta http-equiv="refresh" content="0;url=/cloudsim/inside/cgi-bin/home" />
    <title>CloudSim</title>
</head>
<body style="text-align:center;padding-top:75px;background-color: #f7f7f7;">
   <img src="/cloudsim/js/images/CloudSim_Logo.png" width="200px"/><br/>
   <img src="/cloudsim/js/images/loading.gif" width="200px"/>
</body>
<html>
"""
print(page)