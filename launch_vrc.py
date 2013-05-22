#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import yaml

# This script is meant to be run on the same machine that's running the "papa
# cloudsim."  It'll talk through redis to the local cloudsim to make it launch
# "junior cloudsims," each of which will in turn launch an associated
# constellation.

# We need to import from part of ourself
daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
  'cloudsimd'))
sys.path.insert(0, daemon_path)
from cloudsimd import launch_constellation

USAGE = 'Usage: launch_vrc.py <teams.yaml>'

class Launcher:

    def __init__(self, argv):
        self.teams_yaml = None
        self.teams = {}
        self.parse_args(argv)

    def parse_args(self, argv):
        if len(argv) != 2:
            raise Exception(USAGE)
        self.teams_yaml = sys.argv[1]

    def load(self):
        with open(self.teams_yaml) as f:
            teams = yaml.load_all(f)
            # Build up a dictionary keyed on team ID.
            for t in teams:
                if t is None:
                    continue
                # A bit of sanity checking
                required_keys = ['username', 'team', 'cloudsim', 'quad']
                if not set(required_keys) <= set(t.keys()):
                    raise Exception("Missing one or more required keys")
                if type(t['username']) != type(list()):
                    raise Exception("username field must be a list")
                # Transform the constellation instance names, which use
                # underscores, to configuration types, which use spaces.
                t['cloudsim'] = t['cloudsim'].replace('_', ' ')
                t['quad'] = t['quad'].replace('_', ' ')
                self.teams[t['team']] = t
        print(self.teams)

    def launch(self, team_id):
        team = self.teams[team_id]
        # TODO: handle multiple users in the input file
        username = team['username'][0]
        configuration = team['cloudsim']   
        # We pass the final constellation type as optional args
        args = team['quad']
        print('Launching (%s,%s,%s)'%(username, configuration, args))
        launch_constellation(username, configuration, args)

    def go(self):
        self.load()
        for t in self.teams:
            self.launch(t)

if __name__ == '__main__':
    l = Launcher(sys.argv)
    l.go()
