#!/usr/bin/env python

"""
This program requires a YAML file and a ssh key to access the VRC portal. The
YAML file contains a list of teams, with the team information (name, timezone,
cloudsim constellation, ...). The program performs the next operations:

1. Create a text file with one row per team. The row contains the teamID and
   its CloudSim IP (separated with a space). The CloudSim IP is retrieved from
   the local Redis.
2. Scp the file to the vrcportal using its ssh key.
3. Run a script on the vrcportal to update its database.
"""
import argparse
import os
import sys
import tempfile
import yaml
import subprocess

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)

from cloudsimd import cloudsimd

UPDATE_PORTAL_PROGRAM = 'sudo /var/www/vrc-portal/vrc_attach_cloudsims.py'
NORMAL = '\033[00m'
RED = '\033[0;31m'


def get_constellation_info(my_constellation):
    '''
    Look up a given constellation on Redis
    @param my_constellation Constellation id (string)
    '''
    for constellation in cloudsimd.list_constellations():
        if constellation['constellation_name'] == my_constellation:
            return constellation
    return None


def add(team, portal_file):
    # Get the cloudsim constellation associated to this team
    constellation = team['cloudsim']
    cloudsim = get_constellation_info(constellation)

    # Bad news. The team is not found
    if cloudsim is None:
        return

    # Get the Team CloudSim IP
    cs_ip = cloudsim['simulation_ip']

    new_entry = team['team'] + ' ' + cs_ip + '\n'
    portal_file.write(new_entry)


def go(teams_file, portal_key, one_team_only, user, portal_url):
    '''
    Feed a set of CloudSim instances with each set of tasks.
    @param teams_file YAML file with the team information
    @param portal_key Private key to access into the VRC portal
    @param one_team_only Attach CS only for one team (if the arg is not None)
    @param user VRC Portal user (default: ubuntu)
    @param portal_url VRC Portal URL (default: vrcportal.osrfoundation.org)
    '''
    try:
        # Create text temp file with one line per team
        # TeamID CloudSimIP
        with tempfile.NamedTemporaryFile() as temp_file:

            # Read YAML teams file
            with open(teams_file) as teamsf:
                info = yaml.load(teamsf)

                for team in info['teams']:
                    if ((one_team_only and team['team'] == one_team_only) or
                       not one_team_only):

                        # Add a new entry (team, CloudSimIP) into the temp file
                        add(team, temp_file)

            temp_file.flush()

            # Prepare the private key if present
            identity_opt = ''
            if portal_key:
                identity_opt = '-i ' + portal_key

            # Updload the text file into the VRC Portal
            cmd = ('scp ' + identity_opt + ' ' + temp_file.name + ' ' +
                   user + '@' + portal_url + ':' + temp_file.name)

            subprocess.check_call(cmd.split())

            # Update the VRC Portal's database
            cmd = ('ssh ' + identity_opt + ' ' + user + '@' + portal_url +
                   ' ' + UPDATE_PORTAL_PROGRAM + ' ' + temp_file.name)
            subprocess.check_call(cmd.split())

    except Exception, excep:
        print ('%sError reading teams file (%s): %s%s'
               % (RED, teams_file, repr(excep), NORMAL))


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Attach CloudSims to teams into the VRC Portal'))

    parser.add_argument('teams_file', help='YAML file with the team info')
    parser.add_argument('-k', '--portal-key',
                        help='Ssh key for the VRC Portal')
    parser.add_argument('-t', '--team',
                        help='Attach CloudSim only for this team')
    parser.add_argument('-u', '--user', help='VRC Portal user',
                        default='ubuntu')
    parser.add_argument('-p', '--portal-url', help='VRC Portal URL',
                        default='vrcportal-test.osrfoundation.org')

    # Parse command line arguments
    args = parser.parse_args()
    arg_teams_file = args.teams_file
    arg_portal_key = args.portal_key
    arg_team = args.team
    arg_user = args.user
    arg_portal_url = args.portal_url

    # Attach the cloudsims!
    go(arg_teams_file, arg_portal_key, arg_team, arg_user, arg_portal_url)
