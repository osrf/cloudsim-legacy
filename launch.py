#!/usr/bin/env python

# IMPORTANT: this script is used when a freshly minted cloudsim auto-starts
# a new constellation.  Don't change the interface or behavior of this script
# without also tracking down where it's being called from code.

from __future__ import print_function
import sys
import os
import redis
import time

daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cloudsimd'))
sys.path.insert(0, daemon_path)
print(daemon_path)

# Wait for evidence that cloudsimd is running
r = redis.Redis()
while r.get('cloudsim_ready') is None:
    time.sleep(0.5)

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



