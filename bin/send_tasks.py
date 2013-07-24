#!/usr/bin/env python

"""
This program requires a YAML file. The file contains a list of teams,
with the team information (name, timezone, cloudsim constellation, ...) and the
list of tasks with its information (title, latency,
uplink, local times to start/stop the task, ...). For each team, this program
performs the next operations:
  1. Create a set of tasks according to the YAML tasks file.
  2. Convert the local start/stop times to UTC.
  3. Update a JSON file containing the tasks into the Team's CloudSim.
  4. Load the set of tasks into Redis running on Team's CloudSim.

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

import pytz
import argparse
import yaml
import json
import os
import sys
import tempfile
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


def create_task(team, tasks):
    '''
    Generate a python list containing the set of tasks for a given team
    @param team Dictionary containing team information (accounts, timezone, ...)
    @param tasks Python dictionary containing the list of tasks
    '''
    # Create a dictionaty with the tasks (key = task_id)
    all_tasks = {}

    for task in tasks:
        key = task['task_id']
        all_tasks[key] = task

    my_tasks = []
    counter = 0
    my_task_sequence = team['task_sequence']
    for my_task_id in my_task_sequence:

        if my_task_id not in all_tasks:
            sys.stdout.write('%sTeam %s: Unable to load task %s.'
                             ' Task not found%s\n'
                             % (RED, team['team'], my_task_id, NORMAL))
            continue

        my_task = all_tasks[my_task_id].copy()

        # Get the start and stop local datetimes
        naive_dt_start = my_task['local_start']
        naive_dt_stop = my_task['local_stop']

        local = pytz.timezone(team['timezone'])
        local_dt_start = local.localize(naive_dt_start, is_dst=None)
        local_dt_stop = local.localize(naive_dt_stop, is_dst=None)

        # Add the UTC start/stop time of the task using the timezone
        utc_dt_start = local_dt_start.astimezone(pytz.utc)
        utc_dt_stop = local_dt_stop.astimezone(pytz.utc)

        # Convert from datetime to a string in ISO 8061 format
        # Note: CloudSim will take the local_start and local_stop values as UTC.
        # Also we need to ensure that no offset string is appended, because
        # that confuses the CloudSim code that reads it.
        #my_task['local_start'] = local_dt_start.isoformat(' ')

        #my_task['local_stop'] = local_dt_stop.isoformat(' ')
        #my_task['utc_start'] = utc_dt_start.isoformat(' ')
        #my_task['utc_stop'] = utc_dt_stop.isoformat(' ')
        my_task['local_start'] = utc_dt_start.replace(tzinfo=None).isoformat(' ')
        my_task['local_stop'] = utc_dt_stop.replace(tzinfo=None).isoformat(' ')

        # A team ClousSim will use this command to update its task list
        my_task['command'] = 'create_task'

        # Constellation id containing the sim, where the tasks will run
        my_task['constellation'] = team['quad']

        # Don't let ros_args be null
        if not my_task['ros_args']:
            my_task['ros_args'] = ''

        # Add the modified task to the list
        my_tasks.append(my_task)

        counter += 1

    return (my_tasks, counter)


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    @param my_constellation Constellation id (string)
    '''
    for constellation in cloudsimd.list_constellations():
        if (('constellation_name' in constellation) and
           (constellation['constellation_name'] == my_constellation)):
            return constellation
    return None


def feed_cloudsim(team, tasks, user, is_verbose, dry_run):
    '''
    For a given team, create a list of tasks, upload them to its cloudsim,
    and update Redis with the new task information.
    @param team Dictionary containing team information (accounts, timezone, ...)
    @param tasks Python dictionary containing the list of tasks
    @param user CloudSim user (default: ubuntu)
    @param is_verbose If True, show some stats
    '''
    # Create the new list of tasks
    cs_tasks, num_tasks = create_task(team, tasks)

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

    # Convert the CloudSim list of tasks from a python list to a JSON temp file
    cs_json_tasks = json.dumps(cs_tasks)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(cs_json_tasks)
        temp_file.flush()

        # Scp the JSON into the team's CloudSim
        ssh = sshclient.SshClient(key_dir, key_name, user, ip)
        if not dry_run:
            ssh.upload_file(temp_file.name, temp_file.name)

    #print basepath
    # Upload the script to update the set of tasks
    if not dry_run:
        ssh.upload_file(os.path.join(basepath, 'bin/', UPDATE_PROGRAM), '')

    # Update Redis with the new information sent
    cmd = ('./' + UPDATE_PROGRAM + ' ' + temp_file.name)
    if not dry_run:
        out = ssh.cmd(cmd)
        print 'Ran %s; output:\n  %s'%(cmd, out)
    else:
        print 'Would have run: %s'%(cmd)

    # Print stats if verbose mode is activated
    if is_verbose:
        sys.stdout.write('Team %s: %d tasks loaded into CloudSim\n' %
                        (team['team'], num_tasks))


def go(yaml_file, one_team_only, user, is_verbose, dry_run):
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
                    Thread(target=feed_cloudsim,
                           args=[team, info['tasks'], user, is_verbose, dry_run]).start()

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
    parser.add_argument('-n', '--dry-run', action='store_true', default=False, 
                        help='Dry run')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Show verbose output of the command')

    # Parse command line arguments
    args = parser.parse_args()
    arg_yaml_file = args.yaml_file
    arg_team = args.team
    arg_user = args.user
    arg_verbose = args.verbose
    arg_dry_run = args.dry_run

    #user = os.system('whoami')
    #if user is not "root":
    #    print "You should be running this command as root."
    #    sys.exit(1)

    # Feed the tasks!
    go(arg_yaml_file, arg_team, arg_user, arg_verbose, arg_dry_run)
