#!/usr/bin/env python

# This script runs as a daemon and measures the latency to reach a host. Every second, 
# this value is updated and the result is saved in a redis database with a specific key.

import sys
import daemon
import time
import redis
import subprocess

NPACKET = 1
UNREACHABLE = 99999
CURRENT_LATENCY_KEY = 'ts_currentLatency'

USAGE="""USAGE: ts_sniffer.py <host>
  E.g.: ts_snifer.py 11.8.0.2"""

def parse_args(argv):
    if len(argv) != 2:
        print(USAGE)
        sys.exit(1)
    host = argv[1]

    return host

def get_ping_time(_host):
     
    cmd = "fping {host} -C {npacket} -q".format(host = _host, npacket = NPACKET)
    try:
        output = subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        print 'Output: ', output
    except subprocess.CalledProcessError as e:
        print e.output
        return -1
    
    # Calculate the mean of all the latencies measured for the destination host
    latencies = [float(latency) for latency in output.strip().split(':')[-1].split() if latency != '-']

    if len(latencies) > 0:
        return sum(latencies) / len(latencies)
    return -2

def runDaemon(_host):
    r = redis.Redis('localhost')
    with daemon.DaemonContext(stdout=sys.stdout, stderr=sys.stdout):
        while True:
            currentLatency = get_ping_time(_host)
            print 'Latency: ', str(currentLatency)
            time.sleep(1)
            if currentLatency >= 0:
                r.set(CURRENT_LATENCY_KEY, currentLatency)                    
            else:
                r.set(CURRENT_LATENCY_KEY, UNREACHABLE)
    
if __name__ == "__main__":
    host = parse_args(sys.argv)
    runDaemon(host)
