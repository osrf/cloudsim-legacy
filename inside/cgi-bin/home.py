#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header, get_meta, get_frame
cgitb.enable()


email = authorize()
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)
version = get_cloudsim_version_txt()

user_info = json.dumps({'user':email, 'role':role})
scripts = get_javascripts()

print_http_header()
meta = get_meta()
frame = get_frame(email, 'Home')

page = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>CloudSim - Home</title>""" + meta + """
</head>
<body>""" + frame + """
    <section id="main" class="column">
        <article class="module width_full">
            <header><h3>Welcome to CloudSim</h3></header>
            <div class="module_content">
            <p><h4>CloudSim is an open source web application that launches pre-configured machines designed to run many of
            the most common open source robotic tools, especially the open source robotics simulator Gazebo.</h4></p>
            <p><h4>We are developing CloudSim to support the DARPA Robotics Challenge, in which competitors are designing, programming,
            and testing robots to perform disaster response tasks. In particular, CloudSim and Gazebo will be used heavily in the upcoming
            Virtual Robotics Challenge, wherein approximately 100 teams from around the world will perform interactive, real-time simulation
            tasks in parallel. The cloud provides access to the necessary computing resources for this one time event in a flexible manner.
            In general, cloud-based simulation tasks can be conducted in parallel, for multiple purposes, such as:</h4></p>
            <ul>
                <li><b>validating design decisions</b></li>
                <li><b>optimizing designs</b></li>
                <li><b>predicting performance</b></li>
                <li><b>training users</b></li>
                <li><b>hosting competitions</b></li>
                <li><b>improving robotics education and sharing research</b></li>
            </ul>
            <p><h4>While there are hourly costs associated with computing resources in a cloud environment, there is no upfront cost and little
            administrative effort. CloudSim should make possible simulation campaigns that would otherwise take too long to run on a single
            computer, or be too costly to run at all because of the equipment required.</h4></p>
            </div>
        </article><!-- end of styles article -->
        <div class="clear"></div>
        <div class="spacer"></div>
    </section>
</body>
</html>
"""
print(page)