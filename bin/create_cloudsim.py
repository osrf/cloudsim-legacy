#!/usr/bin/env python

"""
Launch a new cloudsim instance on the cloud
"""

from __future__ import print_function
import sys
import os
import tempfile
import argparse

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Modify PYTHONPATH variable with relative directories to basepath
new_path = os.path.join(basepath, "inside", "cgi-bin")
sys.path.insert(0, new_path)
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)

import common
import cloudsim

# Specify command line arguments
parser = argparse.ArgumentParser(description='Launch a cloudsim instance on the cloud.')
parser.add_argument('username', metavar='ADMIN-EMAIL', help='CloudSim admin gmail account')
parser.add_argument('access_key', metavar='ACCESS-KEY', help='AWS access key')
parser.add_argument('secret_key', metavar='SECRET-KEY', help='AWS secret key')
parser.add_argument('ec2_zone', metavar='EC2-AVAILABILITY-ZONE',
                    help='Amazon EC2 availability zone',
                    choices=['us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d'])

# Parse command line arguments
args = parser.parse_args()
username = args.username
key = args.access_key
secret = args.secret_key
ec2_zone = args.ec2_zone

# Create temporal BOTO configuration file
tmp_fname = tempfile.NamedTemporaryFile()
tmp_fname.close()
cred = common.CloudCredentials(key, secret, fname=tmp_fname.name, ec2_region_name=ec2_zone)
cred.save()

# Launch a cloudsim instance
machine = cloudsim.cloudsim_bootstrap(username, tmp_fname.name)

os.remove(tmp_fname.name)
