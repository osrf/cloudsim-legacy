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

common.print_http_header()
# TODO: remove this copy of index.html and somehow redirect there on logout.
#       I had trouble mixing the Status: and Location: headers to get both 
#       basic auth "logout" and redirect to another page.
print("""
<html>
<head>
  <meta charset="UTF-8" />
  <title>CloudSim Login</title>
  <link rel="stylesheet" type="text/css" href="/css/bootstrap.min.css" />
  <link rel="stylesheet" type="text/css" href="/custom.css" />
</head>
<body>
  <div class="container">
    <div class="login">
      <div class="cs_logo"><img src="/js/images/CloudSimLogo1.svg
        " alt="CloudSim logo" width="180" />
      </div>
      <div class="welcome">
        <p> Welcome! Login to launch and access simulation machines. </p>
      </div>
      <div class="login_form">
        <form action="/cloudsim/inside/cgi-bin/usercheck.py" method="GET">
          <!-- The username and password boxes are disabled here for now, 
               as the current authentication mechanisms either use third-party OpenID
               of pop up a browser-controlled diaglog to get credentials. -->
          <!-- 
          <input class="form-control" type="text" placeholder="Username">
          <input class="form-control" type="password" placeholder="Password">
          -->
          <input type="hidden" name="openid_identifier" value="https://www.google.com/accounts/o8/id"/>
          <input type="hidden" name="openid.ns.ext1" value="http://openid.net/srv/ax/1.0" />
          <input type="hidden" name="openid.ext1.mode" value="fetch_request" />
          <input type="hidden" name="openid.ext1.type.email" value="http://axschema.org/contact/email" />
          <input type="hidden" name="openid.ext1.required" value="email" />
          <button type="submit" class="btn btn-default">Login</button>
        </form>
      </div>
    </div>
    <div id="push"></div>
  </div>

  <div id="footer">
   Brought to you by: <a href="http://osrfoundation.org"> <img src="/js/images/grey_horiz_osrf.svg" alt="CloudSim logo"  width="180" height="50" /></a>
  </div>

 <script src="http://code.jquery.com/jquery.js"></script> 
 <script src="/js/bootstrap.min.js"></script>
</body>
</html>""")

