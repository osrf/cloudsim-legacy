#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import sys
import os
import Cookie

import common

if not common.check_auth_and_generate_response(True):
    sys.exit(0)

in_cookies = Cookie.Cookie()
in_cookies.load(os.environ[common.HTTP_COOKIE])
if common.OPENID_SESSION_COOKIE_NAME in in_cookies:
    out_cookies = Cookie.Cookie()
    out_cookies[common.CLOUDSIM_SESSION_COOKIE_NAME] = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value
    print(out_cookies)
    print("Location: /cloudsim/inside/cgi-bin/console.py\n")
