#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

form = cgi.FieldStorage()
test = form.getfirst('test')
if test:
    test = int(test)

common.print_http_header()
print("<title>Launch a new machine</title>")
print("<h1>Launch a new machine</h1>")
print("<p><b>Usage charges accumulate from the time the machine is launched.</b></p>")

if test:
    print("<form action=\"/cloudsim/inside/cgi-bin/machine_dolaunch.py\" method=\"GET\">")
    print("<input type=\"submit\" value=\"Launch t1.micro (US East)\"/>")
    print("<input type=\"hidden\" name=\"instance_type\" value=\"t1.micro\"/>")
    print("<input type=\"hidden\" name=\"image_id\" value=\"ami-82fa58eb\"/>")
    print("<input type=\"hidden\" name=\"zone\" value=\"useast\"/>")
    print("</form>")

print("<form action=\"/cloudsim/inside/cgi-bin/machine_dolaunch.py\" method=\"GET\">")
print("<input type=\"submit\" value=\"Launch New Simulation Machine\"/> (type cg1.4xlarge, zone US East, <b>$2.10/hour</b>)")
print("<input type=\"hidden\" name=\"instance_type\" value=\"cg1.4xlarge\"/>")
print("<input type=\"hidden\" name=\"image_id\" value=\"ami-98fa58f1\"/>")
print("<input type=\"hidden\" name=\"zone\" value=\"useast\"/>")
print("</form>")

if test:
    print("<form action=\"/cloudsim/inside/cgi-bin/machine_dolaunch.py\" method=\"GET\">")
    print("<input type=\"submit\" value=\"Launch m1.xlarge (US West CA)\"/>")
    print("<input type=\"hidden\" name=\"instance_type\" value=\"m1.xlarge\"/>")
    print("<input type=\"hidden\" name=\"image_id\" value=\"ami-5965401c\"/>")
    print("<input type=\"hidden\" name=\"zone\" value=\"uswest-ca\"/>")
    print("</form>")


common.print_footer()
