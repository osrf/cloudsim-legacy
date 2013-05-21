#!/usr/bin/env python
from __future__ import print_function
import sys
import os

daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cloudsimd'))
sys.path.insert(0, daemon_path)
print(daemon_path)

from cloudsimd import launch_constellation

print (sys.argv)

username = sys.argv[1]
configuration = sys.argv[2]

args = None
if len(sys.argv) > 3:
    args = sys.argv[3]
    
count = 1
if len(sys.argv) > 4:
    count = int(sys.argv[4])

# launch hugo@osrfoundation.org "OSRF CloudSim 02" "OSRF VRC Constellation nightly 02"

print (sys.argv)
print ('username "%s", configuration "%s", args "%s"'  % (username, configuration, args))
launch_constellation(username, configuration, args)



# CMD= "launch" DATA="{u\'username\': u\'hugo@osrfoundation.org\', u\'configuration\': u\'OSRF CloudSim 01\', u\'command\': u\'launch\

# OSRF VRC Constellation nightly build 01
#  
# 
# team_dir = '/home/hugo/code/team-01'
# boto_path = os.path.join(team_dir, "/boto.ini")
# softlayer_creds_path= os.path.join(team_dir, "/softlayer.json")
# portal_key_path = os.path.join(team_dir, "/cloudsim_portal.key")
# cloudsim_portal_json_path = os.path.join(team_dir, "/cloudsim_portal.json")
# bitbucket_key_path = os.path.join(team_dir, "/cloudsim_bitbucket.key")
# 
# "sudo cp -f  %s /var/www-cloudsim-auth/boto-useast" % boto_path
# "sudo cp -f %s /var/www-cloudsim-auth/softlayer.json" %  softlayer_creds_path
# "sudo cp -f %s /var/www-cloudsim-auth/cloudsim_portal.key" % portal_key_path
# "sudo cp -f %s /var/www-cloudsim-auth/cloudsim_portal.json" % cloudsim_portal_json_path
# "sudo cp -f %s /var/www-cloudsim-auth/cloudsim_bitbucket.key" % bitbucket_key_path
