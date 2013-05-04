#!/usr/bin/env python

"""
Create a set of fake tasks for testing
"""

# ToDo1: Fix the problem of multiples entries in the teams

import pytz
import argparse
import yaml
import json
import os
import sys
import tempfile
from threading import Thread

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)

from launch_utils import sshclient
from cloudsimd import cloudsimd


def create_task(team, runs_file, is_verbose):
    '''
    Generate a python list containing the set of tasks for a given competition
    '''
    team_tasks = []

    # Read YAML runs file
    try:
        with open(runs_file) as runsf:
            runs_info = yaml.load_all(runsf)

            counter = 0
            for task in runs_info:

                task['command'] = 'create_task'
                task['constellation'] = team['quadro']

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

                # Add the modified task to the list
                team_tasks.append(task)

                counter += 1

            if is_verbose:
                print 'Team %s: %d tasks created' % (team['team'], counter)

    except Exception, excep:
        print ('Error reading runs file (%s): %s'
               % (runs_file, repr(excep)))

    return team_tasks


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    '''
    for constellation in cloudsimd.list_constellations():
        if constellation['constellation_name'] == my_constellation:
            return constellation
    return None


def feed_cloudsim(team, runs_file, user, is_verbose):
    cs_tasks = create_task(team, runs_file, is_verbose)

    # Get the cloudsim constellation associated to that team
    constellation = team['cloudsim']
    cloudsim = get_constellation_info(constellation)

    if cloudsim is None:
        return

    directory = cloudsim['constellation_directory']
    machine_name = cloudsim['sim_machine_name']
    key_dir = os.path.join(directory, machine_name)
    ip = cloudsim['simulation_ip']
    key_name = cloudsim['sim_key_pair_name']

    # Convert the CloudSim list of tasks from a python list to JSON
    cs_json_tasks = json.dumps(cs_tasks)
    with tempfile.NamedTemporaryFile() as temp_file:
        temp_file.write(cs_json_tasks)
        temp_file.flush()

        # Scp the JSON to the team CloudSim
        ssh = sshclient.SshClient(key_dir, key_name, user, ip)
        ssh.upload_file(temp_file.name, temp_file.name)

    if is_verbose:
        print 'Team %s: Tasks uploaded' % (team['team'])

    # Upload the script to update the set of tasks
    ssh.upload_file('vrc_update_tasks.py', '')

    # Update Redis with the new information sent
    cmd = ('./vrc_update_tasks.py ' + temp_file.name)
    ssh.cmd(cmd)
    if is_verbose:
        print ('Team %s: Tasks loaded into CloudSim\n---\n' %
              (team['team']))


def feed(teams_file, runs_file, user, is_verbose):
    '''
    Feed a set of CloudSim instances with each set of tasks.
    '''
    # Read YAML teams file
    try:
        with open(teams_file) as teamsf:
            teams_info = yaml.load_all(teamsf)

            # Prepare the task for each team
            for team in teams_info:
                Thread(target=feed_cloudsim,
                       args=[team, runs_file, user, is_verbose]).start()

    except Exception, excep:
        print ('Error reading teams file (%s): %s'
               % (teams_file, repr(excep)))


if __name__ == '__main__':
    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Feed every CloudSim with the task information'))

    parser.add_argument('teams_file', help='YAML file with teams info')
    parser.add_argument('runs_file', help='YAML file with runs info')
    parser.add_argument('-u', '--user', default='ubuntu', help='Cloudsim user')
    parser.add_argument('-v', '--verbose', action='store_true', default=False,
                        help='Show verbose output of the command')

    # Parse command line arguments
    args = parser.parse_args()
    arg_teams_file = args.teams_file
    arg_runs_file = args.runs_file
    arg_user = args.user
    arg_verbose = args.verbose

    # Feed the tasks!
    feed(arg_teams_file, arg_runs_file, arg_user, arg_verbose)
