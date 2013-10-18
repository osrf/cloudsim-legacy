#!/usr/bin/env python

"""
Launch a new cloudsim instance on the cloud
"""

from __future__ import print_function
import sys
import os
import tempfile
import argparse
import time
import shutil


# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)

import cloudsimd.launchers.cloudsim as cloudsim
from cloudsimd.launchers.launch_utils.launch_db import get_cloudsim_version
from cloudsimd.launchers.launch_utils.launch_db import init_constellation_data
from cloudsimd.launchers.launch_utils.launch_db import set_cloudsim_config
from cloudsimd.launchers.launch_utils.launch_db import get_unique_short_name
from cloudsimd.launchers.launch_utils.launch_db import ConstellationState

#  Modify PYTHONPATH variable with relative directories to basepath
new_path = os.path.join(basepath, "inside", "cgi-bin")
sys.path.insert(0, new_path)
import common


def create_cloudsim(username,
                    key,
                    secret,
                    ec2_zone,
                    configuratio,
                    authentication_type,
                    password):
    """
    Returns the ip address of the cloudsim instance created. 
    Supports Google OpenID and Basic Authentication 
    """
    # Create temporal BOTO configuration file
    boto_tmp_file = tempfile.NamedTemporaryFile()
    boto_tmp_file.close()
    cred = common.CloudCredentials(key, secret, fname=boto_tmp_file.name,
                                   ec2_region_name=ec2_zone)
    cred.save()
    
    auto_launch_constellation = None
    
    tmp_machine_dir = tempfile.mkdtemp("cloudsim")
    
    config = {}
    config['cloudsim_version'] = get_cloudsim_version()
    config['boto_path'] = boto_tmp_file.name
    config['machines_directory'] = tmp_machine_dir
    constellation_name = get_unique_short_name('c')
    
    data = {}
    data['username'] = username
    data['cloud_provider'] = 'aws'
    data['configuration'] = configuration
    
    init_constellation_data(constellation_name, data, config)
     
    cloudzip_fname = cloudsim.zip_cloudsim()
    # Launch a cloudsim instance
    cloudsim_ip = cloudsim.launch( constellation_name,
                               tags=data,
                               website_distribution=cloudzip,
                               force_authentication_type=authentication_type,
                               basic_auth_password=password)
    
    print("deleting AWS credentials")
    os.remove(boto_tmp_file.name)
    
    print("deleting cloudsim.zip")
    # this is a directory that contains one zip file
    tmp_dir = os.path.dirname(cloudzip_fname)
    shutil.rmtree(tmp_dir)
    
    print("deleting ssh and vpn keys")
    shutil.rmtree(tmp_machine_dir)
    
    print("temporary files removed")
    return cloudsim_ip


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
    #                    nargs='?',
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
                        choices= ['CloudSim', 'CloudSim-stable'])
    # Parse command line arguments
    args = parser.parse_args()
    
    username = args.username
    key = args.access_key
    secret = args.secret_key
    ec2_zone = args.ec2_zone
    configuration = 'CloudSim-Stable'
    
    authentication_type = "OpenID"
    if args.basic_auth:
        authentication_type = "Basic"
    
    create_cloudsim(username=args.username,
                    key=args.access_key,
                    secret=args.secret_key,
                    ec2_zone=args.ec2_zone,
                    configuration='CloudSim-Stable',
                    authentication_type=authentication_type,
                    password=args.basic_auth)
