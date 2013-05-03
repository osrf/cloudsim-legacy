#!/usr/bin/env python

"""
Create a set of fake tasks for testing
"""

import pytz
import argparse
import yaml
import pprint


def create_task(team, runs_file):
    '''
    Generate a python list containing the set of tasks for a given competition
    '''
    team_tasks = []

    # Read runs YAML file
    #try:
    with open(runs_file) as runsf:
        runs_info = yaml.load_all(runsf)

        for task in runs_info:

            # Get the start and stop local datetimes
            naive_dt_start = task['local_start']
            naive_dt_stop = task['local_stop']

            local = pytz.timezone(team['timezone'])
            local_dt_start = local.localize(naive_dt_start, is_dst=None)
            local_dt_stop = local.localize(naive_dt_stop, is_dst=None)

            # Add the UTC start/stop time of the task using the timezone
            utc_dt_start = local_dt_start.astimezone(pytz.utc)
            utc_dt_stop = local_dt_stop.astimezone(pytz.utc)

            task['utc_start'] = utc_dt_start
            task['utc_stop'] = utc_dt_stop

            # Add the modified task to the list
            team_tasks.append(task)

    #except Exception, excep:
    #    print ('Error reading runs file (%s): %s'
    #           % (runs_file, repr(excep)))

    return team_tasks


def feed(teams_file, runs_file, keys_root_dir, cs_user, cs_dest_dir):
    '''
    Feed a set of CloudSim instances with each set of tasks.
    '''

    '''print 'VRC Task Feeder'
    print 'Team file:', teams_file
    print 'Runs file:', runs_file
    print 'Keys root dir:', keys_root_dir
    print 'CS dest dir:', cs_dest_dir'''

    # Read teams YAML file
    #try:
    with open(teams_file) as teamsf:
        teams_info = yaml.load_all(teamsf)

         # Prepare the task for each team
        for team in teams_info:
            cs_tasks = create_task(team, runs_file)

            #print 'Team:', team['team']
            #pprint.pprint(cs_tasks)

            # Convert the CloudSim list of tasks from a python list to JSON
            # ToDo

            # Scp the JSON to the appropriate CloudSim
            # ToDo

            # Update Redis with the new information sent
            # ToDo

    #except Exception, excep:
    #    print ('Error reading teams file (%s): %s'
    #           % (teams_file, repr(excep)))


if __name__ == '__main__':
    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Feed every CloudSim with the task information'))

    parser.add_argument('teams_file', help='YAML file with teams info')
    parser.add_argument('runs_file', help='YAML file with runs info')
    parser.add_argument('keys_root_dir', help='Directory with ssh keys')
    parser.add_argument('-u', '--user', default='ubuntu',
                        help='CloudSim user to scp the tasks')
    parser.add_argument('CS_dest_dir',
                        help=('CloudSim destination directory where the tasks'
                              'will be remote copied'))

    # Parse command line arguments
    args = parser.parse_args()
    arg_teams_file = args.teams_file
    arg_runs_file = args.runs_file
    arg_keys_root_dir = args.keys_root_dir
    arg_cs_user = args.user
    arg_cs_dest_dir = args.CS_dest_dir

    # Feed the tasks!
    feed(arg_teams_file, arg_runs_file, arg_keys_root_dir,
         arg_cs_user, arg_cs_dest_dir)
