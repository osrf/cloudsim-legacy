#!/usr/bin/env python

"""
Launch a new cloudsim instance on the cloud
"""

from __future__ import print_function
import sys
import os
import tempfile
import argparse
import shutil


# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)

import cloudsimd.launchers.cloudsim  as cloudsim
from cloudsimd.launchers.launch_utils.launch_db import ConstellationState
from cloudsimd.launchers.launch_utils.launch_db import get_unique_short_name

#  Modify PYTHONPATH variable with relative directories to basepath
new_path = os.path.join(basepath, "inside", "cgi-bin")
sys.path.insert(0, new_path)
import common


if __name__ == "__main__":
    # Specify command line arguments
    parser = argparse.ArgumentParser(
                        description='Launch a cloudsim instance on the cloud.\n'
                        'CloudSim supports 2 types of authentication (Google '
                        'OpenID and Basic authentication, using -b).'
                        '\n')
    parser.add_argument('username',
                        metavar='ADMIN-USER',
                        help='CloudSim admin account username for basic '
                        'authentication (or gmail address for Google OpenID)')
    parser.add_argument('-b',
                        '--basic_auth',
                        metavar='ADMIN-PSSWD',
                        help=('Use basic authentication with the supplied '
                        'password (Google OpenID is used by default and does '
                        'not require any password)'),
                        default=None)
    parser.add_argument('access_key',
                        metavar='ACCESS-KEY',
                        help='AWS access key')
    parser.add_argument('secret_key',
                        metavar='SECRET-KEY',
                        help='AWS secret key')
    parser.add_argument('ec2_zone',
                        metavar='EC2-AVAILABILITY-ZONE',
                        help='Amazon EC2 availability zone',
                        choices=['nova',
                                 'us-east-1a',
                                 'us-east-1b',
                                 'us-east-1c',
                                 'us-east-1d',
                                 'eu-west-1a',
                                 'eu-west-1b',
                                 'eu-west-1c',])
    parser.add_argument('config',
                        nargs='?',
                        metavar='CONFIGURATION',
                        help='configuration (CloudSim-stable is the default)',
                        default = 'CloudSim-stable',
                        choices= ['CloudSim', 'CloudSim-stable'])
    # Parse command line arguments
    args = parser.parse_args()

    username = args.username
    key = args.access_key
    secret = args.secret_key
    ec2_zone = args.ec2_zone
    configuration = args.config
    password = args.basic_auth

    authentication_type = "OpenID"
    if args.basic_auth:
        authentication_type = "Basic"

    boto_tmp_file = tempfile.NamedTemporaryFile(delete=False)
    boto_tmp_file_fname = boto_tmp_file.name
    boto_tmp_file.close()

    # create a temporary boto credentials file
    cred = common.CloudCredentials(key, secret, fname=boto_tmp_file_fname,
                                   ec2_region_name=ec2_zone)
    cred.save()

    constellation_name = get_unique_short_name('cc')
    # create a temporary machines directory, to be deleted afterwards
    data_dir = tempfile.mkdtemp("create_cloudsim")
    ip = None
    try:
        ip  = cloudsim.create_cloudsim(username=username,
                        credentials_fname=boto_tmp_file_fname,
                        configuration=configuration,
                        authentication_type=authentication_type,
                        password=password,
                        data_dir=data_dir,
                        constellation_name=constellation_name)
    finally:
        print("deleting AWS credentials")
        os.remove(boto_tmp_file_fname)
       
        print("deleting ssh and vpn keys")
        shutil.rmtree(data_dir)
        print("Cleaning Redis database")
        constellation = ConstellationState(constellation_name)
        constellation.expire(1)
    if ip:
        msg = "CloudSim ready at ip %s, user: %s" % (ip, username)
        if authentication_type == "Basic":
            msg += ", password: %s" % password
        print("%s\n\n" % msg)
