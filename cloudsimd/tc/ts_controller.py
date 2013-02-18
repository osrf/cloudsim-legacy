#!/usr/bin/env python

# This script runs as a daemon and tries to maintain the current latency as
# close to a target latency. The current and target latencies are available 
# in redis database. The script acts as a controller injecting an extra 
# amount of latency every cycle. It runs at 1Hz.

import redis
import commands
import sys
import daemon
import time
import subprocess

MAX_LATENCY = 200.0
TARGET_LATENCY_KEY = 'ts_targetLatency'
CURRENT_LATENCY_KEY = 'ts_currentLatency'

USAGE="""USAGE: ts_controller.py <dev>
  E.g.: ts_controller.py eth0"""

def parse_args(argv):
    if len(argv) != 2:
        print(USAGE)
        sys.exit(1)
    dev = argv[1]

    return dev

r = redis.Redis('localhost')
current = 0.0

def update(_dev):
    global current
    global r
    if r.exists(TARGET_LATENCY_KEY) and r.exists(CURRENT_LATENCY_KEY):
        targetLatency = float(r.get(TARGET_LATENCY_KEY))
        currentLatency = float(r.get(CURRENT_LATENCY_KEY))       
        latency2inject = min(max(0, current + float(targetLatency) - float(currentLatency)), MAX_LATENCY)       
        current = latency2inject
        
        print 'Target: ', targetLatency
        print 'Current: ', currentLatency
        print 'current: ', current

        cmd = "python /usr/local/bin/configure_tc.py {dev} {latency}ms {loss}%".format(dev = _dev, latency = latency2inject, loss = 0)
        #cmd = 'configure_tc.py eth0 0ms 0%'
        print cmd
        
        status = subprocess.call(cmd.split(), shell=True)
        print status
        #(status, output) = commands.getstatusoutput(cmd)
        if status:    # Error case
            print status, 'Error using tc'
            return    
    else:
        print 'Latency keys not available'

def runDaemon(_dev):
    with daemon.DaemonContext(stdout=sys.stdout, stderr=sys.stdout):
        while True:
            update(_dev)
            time.sleep(2)        

if __name__ == "__main__":
    dev = parse_args(sys.argv)
    runDaemon(dev)
                
