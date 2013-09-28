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
                    choices=['nova', 'us-east-1a', 'us-east-1b', 'us-east-1c', 'us-east-1d', 'eu-west-1a', 'eu-west-1b', 'eu-west-1c',])

#parser.add_argument('boto_path', nargs='?', metavar='BOTO-PATH', help='Boto path', default='/var/www-cloudsim-auth/boto-useast')
parser.add_argument('softlayer_path', nargs='?', metavar='SOFTLAYER-PATH', help='SoftLayer path', default='/var/www-cloudsim-auth/softlayer.json')
parser.add_argument('root_dir', nargs='?', metavar='ROOT-DIR', help='Root dir', default='/var/www-cloudsim-auth/machines')
parser.add_argument('cloudsim_portal_key_path', nargs='?', metavar='CLOUDSIM-PORTAL-KEY-PATH', help='CloudSim portal key path', default='/var/www-cloudsim-auth/cloudsim_portal.key')
parser.add_argument('cloudsim_portal_json_path', nargs='?', metavar='CLOUDSIM-PORTAL-JSON-PATH', help='CloudSim portal json path', default='/var/www-cloudsim-auth/cloudsim_portal.json')
parser.add_argument('cloudsim_bitbucket_key_path', nargs='?', metavar='CLOUDSIM-BITBUCKET-KEY-PATH', help='CloudSim BitBucket key path', default='/var/www-cloudsim-auth/cloudsim_bitbucket.key')

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

auto_launch_constellation = None

config = {}
config['cloudsim_version'] = '1.7.0'
config['boto_path'] = tmp_fname.name
config['softlayer_path'] = args.softlayer_path
config['machines_directory'] = args.root_dir
config['cloudsim_portal_key_path'] = args.cloudsim_portal_key_path
config['cloudsim_portal_json_path'] = args.cloudsim_portal_json_path
config['cloudsim_bitbucket_key_path'] = args.cloudsim_bitbucket_key_path
config['other_users'] = []
config['cs_role'] = "admin"
config['cs_admin_users'] = []
config['ec2_zone'] = args.ec2_zone


# Launch a cloudsim instance
machine = cloudsim.cloudsim_bootstrap(username, tmp_fname.name, auto_launch_constellation, config)

print("removing temporary files...")
os.remove(tmp_fname.name)
print("temporary files removed")