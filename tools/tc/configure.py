#!/usr/bin/env python

from __future__ import print_function
import sys
import subprocess
import re

USAGE="""configure.py <dev> <latency> <bandwidth> <loss>
  E.g.: configure.py tun0 100ms 125kbit 10%"""

def parse_args(argv):
    if len(argv) != 5:
        print(USAGE)
        sys.exit(1)
    dev = argv[1]
    latency = argv[2]
    bandwidth = argv[3]
    loss = argv[4]

    return (dev, latency, bandwidth, loss)

def go(argv):
    dev, latency, bandwidth, loss = parse_args(argv)

    # Modify latency and loss
    cmd = 'sudo tc qdisc change dev %s root handle 1:0 netem delay %s loss %s'%(dev, latency, loss)
    print(cmd)
    subprocess.check_call(cmd.split())

    # Modify bandwidth
    #
    # A rule of thumb (http://opalsoft.net/qos/DS-24.htm) seems to be that:
    #  buffer >= 0.001 * rate
    #  limit ~= 0.5 * buffer
    # TODO: look into those numbers more thoroughly
    # 
    # Separate the number and unit in the rate so that we can do math on it
    r = re.compile('([0-9]*)(.*)')
    m = r.match(bandwidth)
    if len(m.groups()) < 1:
        print('Failed to parse %s into value and optional unit'%(bandwidth))
        sys.exit(1)
    bw_val = float(m.groups()[0])
    if len(m.groups()) > 1:
        bw_unit = m.groups()[1]
    buf = 0.001 * bw_val
    limit = 0.5 * buf
    cmd = 'sudo tc qdisc change dev %s parent 1:1 handle 10:0 tbf rate %f%s buffer %f%s limit %f%s'%(dev, bw_val, bw_unit, buf, bw_unit, limit, bw_unit)
    # TODO: haven't figured this out yet
    #print(cmd)
    #subprocess.check_call(cmd.split())

if __name__ == '__main__':
    go(sys.argv)
