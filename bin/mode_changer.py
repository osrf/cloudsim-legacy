#!/usr/bin/env python

from __future__ import print_function
import yaml
import datetime
import sys
import pytz
import time
import os

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
# Add to the pythonpath the cloudsimd.launchers package
new_path = os.path.join(basepath, "cloudsimd", "launchers")
sys.path.insert(0, new_path)
sys.path.insert(0, basepath)
from launch_utils import sshclient
from cloudsimd import cloudsimd

USAGE = 'mode_changer.py <master.yaml> <2013-06-14 07:30:00> <oldmode> <newmode>'
KEY_NAME = 'key-cs'
USER = 'ubuntu'
# Note the quotes added around the search and replace strings.  They're needed
# to ensure that we match only "final" and not "final_destination_dir"
CMD = """sudo sed -i 's/"%s"/"%s"/' /var/www-cloudsim-auth/cloudsim_portal.json"""

class LogMover:

    def __init__(self, master_yaml, local_time, oldmode, newmode):
        self.master_yaml = master_yaml
        self.local_time = datetime.datetime.strptime(local_time, '%Y-%m-%d %H:%M:%S')
        y = yaml.load(open(master_yaml))
        self.teams = y['teams']
        self.oldmode = oldmode
        self.newmode = newmode

    def is_time_passed(self, team):
        # Current time in UTC
        utc_now = datetime.datetime.utcnow()
        # Target time for this team in UTC
        local = pytz.timezone(team['timezone'])
        local_dt = local.localize(self.local_time, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        utc_dt_notz = utc_dt.replace(tzinfo=None)
        #print("%s: %s: %s"%(team['team'], team['timezone'], utc_dt))
        return utc_dt_notz < utc_now
    
    def change_mode(self, team):
        constellations = cloudsimd.list_constellations()
        const = [x for x in constellations if x.has_key('constellation_name') and x['constellation_name'] == team['cloudsim']][0]
        ip = const['simulation_ip']
        key_dir = const['constellation_directory']
        ssh = sshclient.SshClient(key_dir, KEY_NAME, USER, ip)
        cmd = CMD%(self.oldmode, self.newmode)
        print('Executing on team %s: %s'%(team['team'], cmd))
        sys.stdout.flush()
        ssh.cmd(cmd)
        print('Changed mode on %s from %s to %s'%(team['team'], self.oldmode, self.newmode))
        sys.stdout.flush()

    def go(self):
        # First, discard teams for whom the target time has already passed
        all_team_names = [x['team'] for x in self.teams]
        self.teams = [t for t in self.teams if not self.is_time_passed(t)]
        remaining_team_names = [x['team'] for x in self.teams]
        removed_teams = set(all_team_names) - set(remaining_team_names)
        if removed_teams:
            print('Discarding %d teams already in the past: %s'%(len(removed_teams), list(removed_teams)))
            sys.stdout.flush()

        # Loop while there's work to do
        while self.teams:
            time.sleep(30.0)
            # Which ones are now in the past?
            self.teams_passed = [t for t in self.teams if self.is_time_passed(t)]
            # Process each one that's getting removed
            for t in self.teams_passed:
                self.teams.remove(t)
                try:
                    self.change_mode(t)
                except Exception as e:
                    print('Failed to change mode on %s: %s'%(t['team'], e))
                    sys.stdout.flush()
            print(time.ctime(time.time()))
            sys.stdout.flush()
        print('All done')
        sys.stdout.flush()
        
        
if __name__ == '__main__':
    if len(sys.argv) != 5:
        print(USAGE)
        sys.exit(1)
    lm = LogMover(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
    lm.go()
