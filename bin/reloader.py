#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import yaml
import argparse
import time
import re

# This script reads a YAML file listing names of SL machines.  For each, it will
# enable the public IP and the reload the machine. It requires a softlayer.json
# file with credentials sufficient to control the machines.

# The machines.yaml should look like this:
#
# machines:
#  - sim-31
#  - router-31
#  - sim-01
#  - router-01

# We need to import from part of ourself
daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cloudsimd'))
sys.path.insert(0, daemon_path)
from launchers.launch_utils.softlayer import load_osrf_creds, enable_public_ips, reload_servers

class Reloader:

    def __init__(self, argv):
        self.softlayer_json = None
        self.machines_yaml = None
        self.creds = None
        self.machines_to_enable_ip = []
        self.all_machines = []
        self.dry_run = False
        self.parse_args(argv)

    def parse_args(self, argv):
        parser = argparse.ArgumentParser(
           description=('Reload SL machines'))
        parser.add_argument('softlayer_json', help='JSON file with SL credentials')
        parser.add_argument('machines_yaml', help='YAML file with list of machines to be reloaded')
        parser.add_argument('-n', '--dry-run',
                            help='Dry run; do not issue any commands',
                            action="store_true")
        args = parser.parse_args()
        self.softlayer_json = args.softlayer_json
        self.machines_yaml = args.machines_yaml
        self.dry_run = args.dry_run
        
    def load(self):
        self.creds = load_osrf_creds(self.softlayer_json)
        sim_re = re.compile('sim-[0-9][0-9]')
        router_re = re.compile('router-[0-9][0-9]')
        # Parse everything out of the yaml file
        with open(self.machines_yaml) as f:
            data = yaml.load(f)
            if 'machines' not in data:
                raise Exception('No machines tag')
            for m in data['machines']:
                if sim_re.match(m):
                    self.machines_to_enable_ip.append(m)
                    self.all_machines.append(m)
                elif router_re.match(m):
                    self.all_machines.append(m)
                else:
                    raise Exception('Machine did not match expected patterns: %s'%(m))
        if len(self.all_machines) == 0:
            raise Exception('No machines')
        print('Will enable IPs on: %s'%(self.machines_to_enable_ip))
        print('Will reload: %s'%(self.all_machines))

    def go(self):
        self.load()
        print('Enabling public IPs...')
        if not self.dry_run:
            print('  Really enabling (not a dry run)')
            enable_public_ips(self.creds, self.machines_to_enable_ip)
            # This is a hack; it doesn't appear to be possible to know,
            # after issuing the IP enable, whether it has completed quickly
            # or not yet started.
            print('  Sleeping to let transaction finish')
            time.sleep(10.0)
        print('Reloading...')
        if not self.dry_run:
            print('  Really reloading (not a dry run)')
            reload_servers(self.creds, self.all_machines)
        print('Done')

if __name__ == '__main__':
    r = Reloader(sys.argv)
    r.go()
