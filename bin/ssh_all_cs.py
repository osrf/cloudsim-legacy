#!/usr/bin/env python

"""
Program that runs a script into a set of machines.

                            __SIM-01
                           |
                           |__FC-01
                 __ CS-01__|
                |  (CS-01) |__FC-01
                |  [tasks] |
                |          |__Router-01
                |             (quad-01)
      CS-Local__|
                |
                |           __SIM-02
                |          |
                |          |__FC-02
                |__ CS-02__|
                   (CS-02) |__FC-02
                   [tasks] |
                           |__Router-02
                              (quad-02)
"""

import argparse
import os
import sys
from threading import Thread

NORMAL = '\033[00m'
RED = '\033[0;31m'
UPDATE_PROGRAM = 'update_tasks.py'

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)

from launch_utils import sshclient
from cloudsimd import cloudsimd


def run(cloudsim, upload_only, script):
    '''
    For a given cloudsim, run the specified script in a set of machines
    @param cloudsim_const
    @param upload_only If True do not execute the script
    @param script Script file that will be remotely executed
    '''
    # Get the CloudSim credentials
    directory = cloudsim['constellation_directory']
    machine_name = 'cs'
    key_dir = os.path.join(directory, machine_name)
    ip = cloudsim['simulation_ip']
    key_name = 'key-cs'

    # Scp the script into the CloudSim Jr
    dest = os.path.join('/tmp', os.path.basename(script))
    ssh = sshclient.SshClient(key_dir, key_name, 'ubuntu', ip)
    ssh.upload_file(script, dest)

    if not upload_only:
        # Run the script
        ssh.cmd(dest)


def go(upload_only, script, ):
    '''
    Run a script in a set of machines.
    @param upload_only If True do not execute the script
    @param script Script file that will be remotely executed
    '''

    CLOUDSIM_PREFIX = 'OSRF_CloudSim_'

    try:
        # Iterate over the list of CloudSims
        for constellation in cloudsimd.list_constellations():
            name = constellation['constellation_name']

            # Filter only the cloudsim constellations
            if name.startswith(CLOUDSIM_PREFIX):
                Thread(target=run, args=[constellation, upload_only, script]).start()

    except Exception, excep:
        print (RED + 'Error getting constellation list: %s + NORMAL'
               % repr(excep))


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Run a script in a set of machines'))

    parser.add_argument('-u', '--upload_only', action='store_true', default=False,
                        help='Just upload the file, do not execute it')
    parser.add_argument('script', help='Script to be executed in each machine')

    # Parse command line arguments
    args = parser.parse_args()
    arg_upload_only = args.upload_only
    arg_script = args.script

    '''user = os.system('whoami')
    if user is not 'root':
        print "You should be running this command as root."
        sys.exit(1)'''

    # Run the script!
    go(arg_upload_only, arg_script)
