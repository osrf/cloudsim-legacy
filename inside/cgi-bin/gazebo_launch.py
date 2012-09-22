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
print("<title>Configure and Launch Gazebo on %s</title>"%(machine_id))
print("<h1>Configure and Launch Gazebo on %s</h1>"%(machine_id))

print("<h2>Install Prerequisites</h2>")
print("<p>If you need extra packages installed on this simulation machine, you can specify them here.  Click Install to install them on the simulation machine.</p>")
print("<p><form action=\"/cloudsim/inside/cgi-bin/machine_doaptget.py\" method=\"GET\">")
print("Packages (space-separated) to install via <tt>apt-get</tt>:")
print("<input type=\"text\" name=\"aptgetlist\"/>")
print("<input type=\"submit\" value=\"Install\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form></p>")

# TODO: allow rosinstall 

print("<h2>Start Gazebo</h2>")
print("<p>To start Gazebo on this simulation machine, provide the package and launch file names, and optionally arguments (as you would normally pass to roslaunch).  Then press Start below.</p>")
print("<form action=\"/cloudsim/inside/cgi-bin/gazebo_dolaunch.py\" method=\"GET\">")
print("Package name:")
print("<input type=\"text\" name=\"package\"/>")
print("Launch file name:")
print("<input type=\"text\" name=\"launchfile\"/>")
print("Launch file arguments (optional):")
print("<input type=\"text\" name=\"launchargs\"/><br>")
print("<input type=\"submit\" value=\"Start\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form>")
print("<h2>Stop Gazebo</h2>")
print("<p>To stop Gazebo on this simulation machine, press Stop below.</p>")
print("<form action=\"/cloudsim/inside/cgi-bin/gazebo_dokill.py\" method=\"GET\">")
print("<input type=\"submit\" value=\"Stop\"/>")
print("<input type=\"hidden\" name=\"%s\" value=\"%s\"/>"%(common.MACHINE_ID_VARNAME, machine_id))
print("</form>")
common.print_footer()
