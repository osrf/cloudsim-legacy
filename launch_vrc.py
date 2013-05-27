#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import yaml
import tempfile
import json
import argparse
import time

# This script is meant to be run on the same machine that's running the "papa
# cloudsim."  It'll talk through redis to the local cloudsim to make it launch
# "junior cloudsims," each of which will in turn launch an associated
# constellation.

# We need to import from part of ourself
daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
  'cloudsimd'))
sys.path.insert(0, daemon_path)
from cloudsimd import launch_constellation

class Launcher:

    def __init__(self, argv):
        self.teams_yaml = None
        self.data = None
        self.team = None
        self.teams = {}
        self.auto_launch_configuration = False
        self.softlayer_credentials = {}
        self.additional_cs_admins = []
        self.parse_args(argv)
        self.tmpdir = tempfile.mkdtemp()
        print('Storing temporary files, including private credentials, in %s.  Be sure to delete this directory after the launch.' % (self.tmpdir))

    def parse_args(self, argv):
        parser = argparse.ArgumentParser(
           description=('Launch VRC constellations'))
        parser.add_argument('teams_file', help='YAML file with the team info')
        parser.add_argument('-t', '--team',
                            help='Attach CloudSim only for this team',)
        parser.add_argument('-a', '--auto_launch',
                            help='Also provision the constellation once CloudSim is ready',
                            action="store_true")
        args = parser.parse_args()
        self.teams_yaml = args.teams_file
        self.team = args.team
        print(args)
        self.auto_launch = args.auto_launch
        
    def load(self):
        # Parse everything out of the yaml file
        with open(self.teams_yaml) as f:
            self.data = yaml.load(f)
        # A bit of sanity checking
        required_keys = ['portal_hostname', 'portal_user',
                         'upload_dir', 'final_destination_dir',
                         'live_destination', 'event', 'portal_key_path',
                         'bitbucket_key_path', 'tasks', 'teams',
                         'softlayer_credentials']
        if not set(required_keys) <= set(self.data.keys()):
            raise Exception("Missing one or more required keys")
        if self.data['bitbucket_key_path'] is not None and not os.path.exists(self.data['bitbucket_key_path']):
            raise Exception("Invalid bitbucket key path: %s" % (self.data['bitbucket_key_path']))
        if self.data['portal_key_path'] is not None and not os.path.exists(self.data['portal_key_path']):
            raise Exception("Invalid portal key path: %s" % (self.data['portal_key_path']))
        for s in self.data['softlayer_credentials']:
            required_keys = ['team', 'user', 'api_key']
            if not set(required_keys) <= set(s.keys()):
                raise Exception("Missing one or more required keys")
            self.softlayer_credentials[s['team']] = s

        for t in self.data['teams']:
            # A bit of sanity checking
            required_keys = ['username', 'team', 'cloudsim', 'quad', 'cs_role']
            if not set(required_keys) <= set(t.keys()):
                raise Exception("Missing one or more required keys")
            if type(t['username']) != type(list()):
                raise Exception("username field must be a list")
            if t['team'] not in self.softlayer_credentials:
                raise Exception("no softlayer credentials for team %s" % (t['team']))
            if t['cs_role'] not in ['user', 'officer', 'admin']:
                raise Exception("wrong cloudsim role for team %s" % (t['team']))

            # Transform the constellation instance names, which use
            # underscores, to configuration types, which use spaces.
            t['cloudsim'] = t['cloudsim'].replace('_', ' ')
            t['quad'] = t['quad'].replace('_', ' ')
            self.teams[t['team']] = t

            # Additional cloudsim admin users
            if 'cs_admin_users' in self.data:
                if type(self.data['cs_admin_users']) == type(list()):
                    self.additional_cs_admins = self.data['cs_admin_users']
                else:
                    raise Exception("cloudsim admin users must be a list")

        #print(self.teams)

    def generate_files(self, team_id):
        # Generate the following files:
        #   softlayer.json
        #   cloudsim_portal.json
        softlayer = dict()
        softlayer['api_key'] = self.softlayer_credentials[team_id]['api_key']
        softlayer['user'] = self.softlayer_credentials[team_id]['user']
        self.teams[team_id]['softlayer_fname'] = os.path.join(self.tmpdir, '%s_softlayer.json' % (team_id))
        with open(self.teams[team_id]['softlayer_fname'], 'w') as f:
            f.write(json.dumps(softlayer))
            f.write('\n')

        portal = dict()
        portal['hostname'] = self.data['portal_hostname']
        portal['user'] = self.data['portal_user']
        portal['team'] = team_id
        portal['upload_dir'] = self.data['upload_dir']
        portal['final_destination_dir'] = self.data['final_destination_dir']
        portal['live_destination'] = self.data['live_destination']
        portal['event'] = self.data['event']
        self.teams[team_id]['portal_fname'] = os.path.join(self.tmpdir, '%s_cloudsim_portal.json' % (team_id))
        with open(self.teams[team_id]['portal_fname'], 'w') as f:
            f.write(json.dumps(portal))
            f.write('\n')

    def launch(self, team_id):
        self.generate_files(team_id)
        team = self.teams[team_id]
        # TODO: handle multiple users in the input file
        username = team['username'][0]
        configuration = team['cloudsim']
        # Build a dictionary of configuration for this team
        args = dict()
        # Set auto_launch_configuration to None to not launch a follow-on
        # constellation from the newly created CloudSim Jr.
        if self.auto_launch:
            args['auto_launch_configuration'] = team['quad']
            print("Auto launch configuration: %s" % team['quad'])
        else:
            args['auto_launch_configuration'] = None
        
        args['softlayer_path'] = team['softlayer_fname']
        args['cloudsim_portal_json_path'] = team['portal_fname']
        args['cloudsim_portal_key_path'] = self.data['portal_key_path']
        args['cloudsim_bitbucket_key_path'] = self.data['bitbucket_key_path']
        args['other_users'] = team['username'][1:]
        args['cs_role'] = team['cs_role']
        args['cs_admin_users'] = self.additional_cs_admins
        print('Launching (%s,%s,%s)' % (username, configuration, args))
        launch_constellation(username, configuration, args)

    def go(self):
        self.load()
        if self.team:
            self.launch(self.team)
        else:
            for t in self.teams:
                self.launch(t)
                # make it easy in the network load
                time.sleep(5) 
        print("\n ** Remember to delete %s after the launch has completed **" % (self.tmpdir))

if __name__ == '__main__':
    l = Launcher(sys.argv)
    l.go()
