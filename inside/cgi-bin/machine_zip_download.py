#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import cgi
import cgitb
import os
import sys
import redis
from common.web import UserDatabase
from common.machine_configuration import get_constellation_data

cgitb.enable()

from common import  authorize


def log(msg):
    red = redis.Redis()
    red.publish("machine_zip_download", "[machine_zip_download.py] " + msg)


def get_machine_zip_key(email, constellation_name, machine_name):
    """
    Returns the zip file for the machine. The path may have a "user_" prefix
    if the email does not correspond to an officer or admin
    """
    constellation = get_constellation_data(email, constellation_name)
    directory = constellation['constellation_directory']

    udb = UserDatabase()
    user_is_officer = udb.has_role(email, "officer")
    log("is_officer %s = %s" % (user_is_officer, user_is_officer))
    path = os.path.join(directory,  "%s.zip" % machine_name)
    if not user_is_officer:
        path = os.path.join(directory,  "user_%s.zip" % machine_name)
    log("path is %s" % path)
    return path


def download(filename):

    short_name = os.path.split(filename)[1]
    if short_name.startswith("user_"):
        short_name = short_name.split("user_")[1]
    log("download AS %s" % short_name)
    print("Pragma: public")
    print("Expires: 0")
    print("Cache-Control: must-revalidate, post-check=0, pre-check=0")
    print("Cache-Control: public")
    print("Content-Description: File Transfer")
    print("Content-type: application/octet-stream")
    print('Content-Disposition: attachment; filename="%s"' % short_name)
    print("Content-Transfer-Encoding: binary")
    size = os.path.getsize(filename)
    print("Content-Length: %s" % size)
    print ("")

    with open(filename, 'rb') as f:
        while True:
            data = f.read(4096)
            sys.stdout.write(data)
            if not data:
                break

email = authorize()

form = cgi.FieldStorage()
constellation_name = form.getfirst('constellation')
machine_name = form.getfirst('machine')

filename = get_machine_zip_key(email, constellation_name, machine_name)

log("constellation_name: %s" % constellation_name)
log("machine_name: %s" % machine_name)
log("filename %s" % filename)

if os.path.exists(filename):
    log("EXISITS")
    download(filename)
else:
    print ("Status: 404 Not Found")
    print ("Content-Type: text/html\n\n")
    print ("<h1>404 File not found!</h1>")
    print("<br>" + filename + "")
