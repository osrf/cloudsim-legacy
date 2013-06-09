#!/usr/bin/env python

"""
This program requires a YAML file. The file contains a list of teams,
with the team information (name, timezone, cloudsim constellation, ...) and the
list of tasks with its information (title, latency,
uplink, local times to start/stop the task, ...). For each team, this program
removes the current list of tasks
"""

import argparse
import yaml
import os
import sys
from threading import Thread

NORMAL = '\033[00m'
RED = '\033[0;31m'
REMOVE_TASKS_PROGRAM = 'remove_tasks.py'

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)

from launch_utils import sshclient
from cloudsimd import cloudsimd


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    @param my_constellation Constellation id (string)
    '''
    for constellation in cloudsimd.list_constellations():
        if constellation['constellation_name'] == my_constellation:
            return constellation
    return None


def remove_tasks(team, user, is_verbose):
    '''
    For a given team, remove its list of tasks.
    @param team Dictionary containing team information (accounts, timezone, ...)
    @param user CloudSim user (default: ubuntu)
    @param is_verbose If True, show some stats
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

    # Scp the JSON into the team's CloudSim
    ssh = sshclient.SshClient(key_dir, key_name, user, ip)

    # Upload the script to update the set of tasks
    ssh.upload_file(os.path.join(basepath, 'bin/', REMOVE_TASKS_PROGRAM), 'cloudsim/bin')

    # Update Redis with the new information sent
    cmd = ('./cloudsim/bin/' + REMOVE_TASKS_PROGRAM)
    ssh.cmd(cmd)

    # Print stats if verbose mode is activated
    if is_verbose:
        sys.stdout.write('Team %s: Tasks removed\n' % team['team'])


def go(yaml_file, one_team_only, user, is_verbose):
    '''
    Feed a set of CloudSim instances with each set of tasks.
    @param yaml_file YAML file with the team and tasks information
    @param one_team_only Create tasks only for one team (if the arg is not None)
    @param user CloudSim user (default: ubuntu)
    @param is_verbose If True, show some stats
    '''
    try:
        # Read YAML teams file
        with open(yaml_file) as infof:
            info = yaml.load(infof)

            # Start a thread for each team and load the tasks
            for team in info['teams']:
                if ((one_team_only and team['team'] == one_team_only) or
                   not one_team_only):
                    Thread(target=remove_tasks,
                           args=[team, user, is_verbose]).start()

    except Exception, excep:
        print (RED + 'Error reading yaml file (%s): %s + NORMAL'
               % (yaml_file, repr(excep)))


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Send a task list to a remote cloudsim'))

    parser.add_argument('yaml_file', help='YAML file with the team and tasks info')
    parser.add_argument('-t', '--team', help='Feed tasks only for this team')
    parser.add_argument('-u', '--user', default='ubuntu', help='Cloudsim user')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Show verbose output of the command')

    # Parse command line arguments
    args = parser.parse_args()
    arg_yaml_file = args.yaml_file
    arg_team = args.team
    arg_user = args.user
    arg_verbose = args.verbose

    #user = os.system('whoami')
    #if user is not "root":
    #    print "You should be running this command as root."
    #    sys.exit(1)

    # Feed the tasks!
    go(arg_yaml_file, arg_team, arg_user, arg_verbose)
