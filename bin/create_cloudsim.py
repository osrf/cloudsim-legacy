#!/usr/bin/env python

from __future__ import print_function

import sys
import os

import tempfile


usage = """

Launch a cloudsim instance on AWS

usage: create_cloudsim.py username key secret_key

"""

if len(sys.argv) != 4:
    print(usage)
    sys.exit(1)

#print(sys.argv)

username = sys.argv[1]
key = sys.argv[2]
secret = sys.argv[3]


new_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "inside", "cgi-bin")

sys.path.append(new_path)
print(new_path)

new_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "cloudsimd", "launchers")

sys.path.append(new_path)
print(new_path)

import common
import cloudsim

from common import CloudCredentials

tmp_fname = tempfile.NamedTemporaryFile()

tmp_fname.close()
cred = CloudCredentials(key, secret, fname = tmp_fname.name)

cred.save()
machine = cloudsim.cloudsim_bootstrap(username, tmp_fname.name)


    
os.remove(tmp_fname.name)