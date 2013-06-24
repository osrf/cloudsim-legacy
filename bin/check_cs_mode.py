#!/usr/bin/env python

"""
This program requires a YAML file. The file contains a list of teams,
with the team information (name, timezone, cloudsim constellation, ...) and the
list of tasks with its information (title, latency,
uplink, local times to start/stop the task, ...). For each team, this program
checks the cloudsim version and compared with the one passed as an argument
"""

import argparse
import yaml
import os
import sys
from threading import Thread
import subprocess

NORMAL = '\033[00m'
RED = '\033[0;31m'
DEFAULT_SSH_OPTS = ('-o UserKnownHostsFile=/dev/null '
                    '-o StrictHostKeyChecking=no '
                    '-o ConnectTimeout=5')

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)

from cloudsimd import cloudsimd


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    @param my_constellation Constellation id (string)
    '''
    for constellation in cloudsimd.list_constellations():
        if 'constellation_name' in constellation and constellation['constellation_name'] == my_constellation:
            return constellation
    return None


def check_mode(team, mode, user):
    '''
    For a given team, retrieve its competition mode (practice, final, ...).
    @param team Dictionary containing team information (accounts, timezone, ...)
    @param mode Expected CloudSim mode
    @param user CloudSim user (default: ubuntu)
    '''
    # Get the cloudsim constellation associated to this team
    constellation = team['cloudsim']
    cloudsim = get_constellation_info(constellation)

    if cloudsim is None:
        return

    # Get the CloudSim credentials for this team
    directory = cloudsim['constellation_directory']
    machine_name = 'cs'
    key_dir = os.path.join(directory, machine_name)
    ip = cloudsim['simulation_ip']
    key_name = 'key-cs'

    key = os.path.join(key_dir, key_name + '.pem')
    cmd = ('ssh ' + DEFAULT_SSH_OPTS + ' -i ' + key + ' ' + user + '@' + ip +
           ' sudo cat /var/www-cloudsim-auth/cloudsim_portal.json | tr -d " " | grep \\"event\\":\\"' + mode + '\\"')

    po = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = po.communicate()

    if po.returncode != 0:
        print 'Incorrect mode in %s' % constellation


def go(yaml_file, mode, one_team_only, user):
    '''
    Check the mode of a list of CloudSim instances.
    @param yaml_file YAML file with the team and tasks information
    @param version Expected cloudsim version
    @param one_team_only Create tasks only for one team (if the arg is not None)
    @param user CloudSim user (default: ubuntu)
    '''
    try:
        # Read YAML teams file
        with open(yaml_file) as infof:
            info = yaml.load(infof)

            # Start a thread for each team and load the tasks
            for team in info['teams']:
                if ((one_team_only and team['team'] == one_team_only) or
                   not one_team_only):
                    Thread(target=check_mode,
                           args=[team, mode, user]).start()

    except Exception, excep:
        print (RED + 'Error reading yaml file (%s): %s + NORMAL'
               % (yaml_file, repr(excep)))


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Checks if all the CloudSims have the correct mode (practice, final)'))

    parser.add_argument('yaml_file', help='YAML file with the team and tasks info')
    parser.add_argument('mode', help='Expected CloudSim mode')
    parser.add_argument('-t', '--team', help='Check mode only for this team')
    parser.add_argument('-u', '--user', default='ubuntu', help='Cloudsim user')

    # Parse command line arguments
    args = parser.parse_args()
    arg_yaml_file = args.yaml_file
    arg_mode = args.mode
    arg_team = args.team
    arg_user = args.user

    go(arg_yaml_file, arg_mode, arg_team, arg_user)
