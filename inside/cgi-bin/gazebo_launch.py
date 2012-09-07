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
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)

common.print_http_header()
print("<title>Configure and launch Gazebo</title>")
print("<h1>Configure and launch Gazebo</h1>")

print("<h2>Install prerequisites</h2>")
print("<form action=\"/cloudsim/inside/cgi-bin/machine_doaptget.py\" method=\"GET\">")
print("Package to install via <tt>apt-get</tt>:")
print("<input type=\"text\" name=\"aptgetlist\"/>")
print("<input type=\"submit\" value=\"Install\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form>")

# TODO: allow rosinstall 

print("<h2>Start / stop Gazebo</h2>")
print("<form action=\"/cloudsim/inside/cgi-bin/gazebo_dolaunch.py\" method=\"GET\">")
print("Package name:")
print("<input type=\"text\" name=\"package\"/>")
print("Launch file name:")
print("<input type=\"text\" name=\"launchfile\"/>")
print("Launch file arguments (optional)):")
print("<input type=\"text\" name=\"launchargs\"/><br>")
print("<input type=\"submit\" value=\"Start\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form>")
print("<form action=\"/cloudsim/inside/cgi-bin/gazebo_dokill.py\" method=\"GET\">")
print("<input type=\"submit\" value=\"Stop\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form>")
common.print_footer()
