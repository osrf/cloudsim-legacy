#!/usr/bin/env python

"""
This program requires two YAML files. The first file contains a list of teams,
with the team information (name, timezone, cloudsim constellation, ...). The
second file contains a list of tasks with its information (title, latency,
uplink, local times to start/stop the task, ...). For each team, this program
performs the next operations:
  1. Create a set of tasks according to the YAML tasks file.
  2. Convert the local start/stop times to UTC.
  3. Update a JSON file containing the tasks to the Team's CloudSim.
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

NORMAL = '\[\033[00m\]'
RED = '\[\033[0;31m\]'

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
    @param team Unique team id (string)
    @param tasks Dictionary containing the task definitions
    '''
    team_tasks = []
    counter = 0
    run_sequence = team['runs']
    for run in run_sequence:

        if not run in tasks:
            print RED + 'Unable to load task %s. Task not found' + NORMAL
            continue

        task = tasks[run]

        # Get the start and stop local datetimes
        naive_dt_start = task['local_start']
        naive_dt_stop = task['local_stop']

        local = pytz.timezone(team['timezone'])
        local_dt_start = local.localize(naive_dt_start, is_dst=None)
        local_dt_stop = local.localize(naive_dt_stop, is_dst=None)

        # Add the UTC start/stop time of the task using the timezone
        utc_dt_start = local_dt_start.astimezone(pytz.utc)
        utc_dt_stop = local_dt_stop.astimezone(pytz.utc)

        # Convert from datetime to a string in ISO 8061 format
        task['local_start'] = local_dt_start.isoformat(' ')
        task['local_stop'] = local_dt_stop.isoformat(' ')
        task['utc_start'] = utc_dt_start.isoformat(' ')
        task['utc_stop'] = utc_dt_stop.isoformat(' ')

        # A team ClousSim will use this command to update its task list
        task['command'] = 'create_task'

        # Constellation id containing the sim, where the tasks will run
        task['constellation'] = team['quadro']

        # Add the modified task to the list
        team_tasks.append(task)

        counter += 1

    return (team_tasks, counter)


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    @param my_constellation Constellation id (string)
    '''
    for constellation in cloudsimd.list_constellations():
        if constellation['constellation_name'] == my_constellation:
            return constellation
    return None


def feed_cloudsim(team, tasks, user, is_verbose):
    '''
    For a given team, create a list of tasks, upload them to its cloudsim,
    and update Redis with the new task information.
    @param team Team id (string)
    @param tasks Dictionary containing the task definitions
    @param user CloudSim user (default: ubuntu)
    @param is_verbose Show some stats if True
    '''
    # Create the new list of tasks
    cs_tasks, num_tasks = create_task(team, tasks)

    # Get the cloudsim constellation associated to this team
    constellation = team['cloudsim']
    cloudsim = get_constellation_info(constellation)

    if cloudsim is None:
        return

    # Get the CloudSim credentials associated to this team
    directory = cloudsim['constellation_directory']
    machine_name = cloudsim['sim_machine_name']
    key_dir = os.path.join(directory, machine_name)
    ip = cloudsim['simulation_ip']
    key_name = cloudsim['sim_key_pair_name']

    # Convert the CloudSim list of tasks from a python list to a JSON temp file
    cs_json_tasks = json.dumps(cs_tasks)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(cs_json_tasks)
        temp_file.flush()

        # Scp the JSON to the team CloudSim
        ssh = sshclient.SshClient(key_dir, key_name, user, ip)
        ssh.upload_file(temp_file.name, temp_file.name)

    # Upload the script to update the set of tasks
    ssh.upload_file('vrc_update_tasks.py', '')

    # Update Redis with the new information sent
    cmd = ('./vrc_update_tasks.py ' + temp_file.name)
    ssh.cmd(cmd)

    # Print stats if verbose mode is activated
    if is_verbose:
        sys.stdout.write('Team %s: %d tasks loaded into CloudSim\n' %
                        (team['team'], num_tasks))


def feed(teams_file, runs_file, one_team_only, user, is_verbose):
    '''
    Feed a set of CloudSim instances with each set of tasks.
    @param teams_file YAML file with the team information
    @param runs_file YAML file with the task definition
    @param one_team_only Create tasks only for one team (if the arg is not None)
    @param user CloudSim user (default: ubuntu)
    @param is_verbose Show some stats if True
    '''
    # Create a dictionaty with the tasks (key = task_id)
    tasks = {}

    # Read YAML runs file
    try:
        with open(runs_file) as runsf:
            runs_info = yaml.load_all(runsf)

            for task in runs_info:
                key = task['task_id']
                tasks[key] = task

    except Exception, excep:
        print (RED + 'Error reading runs file (%s): %s + NORMAL'
               % (runs_file, repr(excep)))
        return

    # Read YAML teams file
    try:
        with open(teams_file) as teamsf:
            teams_info = yaml.load_all(teamsf)

            # Prepare the task for each team
            for team in teams_info:
                if ((one_team_only and team['team'] == one_team_only) or
                   not one_team_only):
                    Thread(target=feed_cloudsim,
                           args=[team, tasks, user, is_verbose]).start()

    except Exception, excep:
        print (RED + 'Error reading teams file (%s): %s + NORMAL'
               % (teams_file, repr(excep)))


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Feed every CloudSim with the task information'))

    parser.add_argument('teams_file', help='YAML file with teams info')
    parser.add_argument('runs_file', help='YAML file with runs info')
    parser.add_argument('-t', '--team', help='Feed tasks only for this team')
    parser.add_argument('-u', '--user', default='ubuntu', help='Cloudsim user')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Show verbose output of the command')

    # Parse command line arguments
    args = parser.parse_args()
    arg_teams_file = args.teams_file
    arg_runs_file = args.runs_file
    arg_team = args.team
    arg_user = args.user
    arg_verbose = args.verbose

    # Feed the tasks!
    feed(arg_teams_file, arg_runs_file, arg_team, arg_user, arg_verbose)
