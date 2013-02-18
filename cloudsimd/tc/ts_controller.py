#!/usr/bin/env python

# This script runs as a daemon and tries to maintain the current latency as
# close to a target latency. The current and target latencies are available 
# in redis database. The script acts as a controller injecting an extra 
# amount of latency every cycle.

import sys
import daemon
import time
import redis
import subprocess
import pid
import string

class TS_Controller:

    # Constants
    MAX_LATENCY = 200.0
    TARGET_LATENCY_KEY = 'ts_targetLatency'
    CURRENT_LATENCY_KEY = 'ts_currentLatency'
    STATIC_INC = 'static'
    DYNAMIC_INC = 'dynamic'
    PID = 'pid'
    STEP = 10.0
    DEBUG = True

    def __init__(self, _dev, _type):
        self.dev = _dev
        self.typec = _type
        self.r = redis.Redis('localhost')
        self.current = 0.0
        self.pid = pid.PID('TS',0, 1, 0, 100)

    def update(self):
        if self.r.exists(TS_Controller.TARGET_LATENCY_KEY) and self.r.exists(TS_Controller.CURRENT_LATENCY_KEY):
            targetLatency = float(self.r.get(TS_Controller.TARGET_LATENCY_KEY))
            currentLatency = float(self.r.get(TS_Controller.CURRENT_LATENCY_KEY))       

            if self.typec == TS_Controller.STATIC_INC: # Type: Static increment/decrement
                if currentLatency < targetLatency:
                    self.current += TS_Controller.STEP
                else:
                    self.current -= TS_Controller.STEP            
            elif self.typec == TS_Controller.DYNAMIC_INC: # Type: Dynamic increment/decrement
                self.current += targetLatency - currentLatency
            elif self.typec == TS_Controller.PID: # Type: PID
                self.pid.setReference((targetLatency - currentLatency) / TS_Controller.MAX_LATENCY)
                self.current += (self.pid.getOutput() / 100.0) * TS_Controller.MAX_LATENCY
            else:
                print '[TS_Controller::update()] Wrong controller type (', str(self.typec, ')')
                return

            latency2inject = min(max(0, self.current), TS_Controller.MAX_LATENCY) 

            cmd = "configure_tc.py {dev} {latency}ms {loss}%".format(dev = self.dev, latency = latency2inject, loss = 0)
            if TS_Controller.DEBUG:
                print 'Command to run: ', cmd
                print 'Target: ', targetLatency
                print 'Current: ', currentLatency
                print 'To inject: ', latency2inject       
            try: 
                status = subprocess.check_call(cmd.split())
            except subprocess.CalledProcessError as e:
                print e.output
                return

            if status:    # Error case
                print status, '[TS_Controller::update()] Error using tc'
                return    
        else:
            print '[TS_Controller::update()] Latency keys not available'


USAGE="""USAGE: ts_controller.py <dev> <static|dynamic|pid> <freq>
  E.g.: ts_controller.py eth0 pid 1"""

def parse_args(argv):
    if len(argv) != 4:
        print(USAGE)
        sys.exit(1)
    dev = argv[1]
    typec = string.lower(argv[2])
    freq = float(argv[3])

    return dev, typec, freq 

def runDaemon(_dev, _typec, _freq):
    with daemon.DaemonContext(stdout=sys.stdout, stderr=sys.stdout):
        ts = TS_Controller(_dev,_typec)
        while True:
            ts.update()
            time.sleep(1.0 / _freq)

if __name__ == "__main__":
    dev, typec, freq = parse_args(sys.argv)
    runDaemon(dev, typec, freq)
                
