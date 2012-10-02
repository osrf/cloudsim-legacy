#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import shutil
import cgitb
cgitb.enable()
import sys

import common

if not common.check_auth_and_generate_response():
    sys.exit(0)

form = cgi.FieldStorage()
machine_id = form.getfirst(common.MACHINE_ID_VARNAME)
package = form.getfirst(common.PACKAGE_VARNAME)
launchfile = form.getfirst(common.LAUNCHFILE_VARNAME)
launchargs = form.getfirst(common.LAUNCHARGS_VARNAME)
common.print_http_header()

if not machine_id or not package or not launchfile:
    print("Error: machine_id, package, and launchfile are all required.")
    print("<a href=\"/cloudsim/inside/cgi-bin/gazebo_launch.py?%s=%s\">Go back</a>.</p>"%(common.MACHINE_ID_VARNAME, machine_id))
    common.print_footer()
    sys.exit(0)
if not launchargs:
    launchargs = ''

email = common.session_id_to_email()
(machines, incompletes) = common.list_machines(email)
matches = [m for m in machines if m.name == machine_id]
if not matches:
    print("Error: machine not found.  Perhaps the machine isn't done being created yet.<br>")
else:
    machine = matches[0]
    #cmd = ['\"source /opt/ros/fuerte/setup.bash && ROS_IP=%s DISPLAY=%s nohup roslaunch %s %s %s >/dev/null 2>/dev/null </dev/null &\"'%(common.OV_SERVER_IP, common.DISPLAY, package, launchfile, launchargs)]
    #cmd = ['source /opt/ros/fuerte/setup.bash && ROS_IP=%s DISPLAY=%s nohup roslaunch %s %s %s >/dev/null 2>/dev/null </dev/null &'%(common.OV_SERVER_IP, common.DISPLAY, package, launchfile, launchargs)]
    
    
    #cmd = ['bash', '-c', '"source /opt/ros/fuerte/setup.bash && ROS_IP=10.8.0.1 DISPLAY=:0 nohup roslaunch pr2_gazebo pr2_empty_world.launch  >/dev/null 2>/dev/null </dev/null"', '&']
    
    script = '". /opt/ros/fuerte/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s %s  >/dev/null 2>/dev/null </dev/null &"'%(common.OV_SERVER_IP, common.DISPLAY, package, launchfile, launchargs)
    
    cmd = ['echo', script, '>start_me.sh']
    
    print("<p>Running the echo: <pre>%s</pre></p>"%(cgi.escape(' '.join(cmd))))
    ret, err = machine.ssh(cmd, args=['-f'])
    print ("ret: %s<p>err: %s<p>" % (ret, err) )
    
    
    cmd = ['at', 'NOW', '<start_me.sh']
    print("<p>Running the following command: <pre>%s</pre></p>"%(cgi.escape(' '.join(cmd))))
    ret, err = machine.ssh(cmd, args=['-f'])
    print ("ret: %s<p>err: %s<p>" % (ret, err) )
    if ret:
        print("<p>Gazebo has been launched; this process can take a few minutes to complete, or to fail.")
    else:
        print("<p>Error: <pre>%s</pre>"%(err))
    print("Return to <a href=\"/cloudsim/inside/cgi-bin/machine_detail.py?%s=%s\">machine details</a> to check status.</p>"%(common.MACHINE_ID_VARNAME, machine_id))

common.print_footer()
