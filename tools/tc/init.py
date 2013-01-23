#!/usr/bin/env python

from __future__ import print_function
import sys
import subprocess

# This script establishes tc (traffic control) rules that will be used to
# manipulate communication over a given interface.  The rules established
# by the script are meant to be no-ops; they don't affect communication now,
# but rather are meant to be modified later.  See configure.sh for an example
# of modification.

USAGE="""USAGE: init.py <dev>
  E.g.: init.py tun0"""

def parse_args(argv):
    if len(argv) != 2:
        print(USAGE)
        sys.exit(1)
    dev = argv[1]

    return dev

def go(argv):
    dev = parse_args(argv)

    # Delete any existing rules (can fail if there weren't any rules, so
    # we don't check the return value)
    cmd = 'sudo tc qdisc del dev %s root'%(dev)
    print(cmd)
    subprocess.call(cmd.split())
    
    # Now we'll add the rules we need, in a hierarchical fashion.  
    # TODO: learn about the implications of the hierarchy and reconsider
    # this particular order (which is patterned after the VRC Technical Guide
    # Section 5.2)
    
    # Add a rule to induce latency and loss, using netem (network emulator)
    cmd = 'sudo tc qdisc add dev %s root handle 1:0 netem delay 0ms loss 0.0%%'%(dev)
    print(cmd)
    subprocess.check_call(cmd.split())
    
    # Add a rule to limit bandwidth, using tbf (token bucket filter)
    # We have to pick numbers here, so pick them high enough to not
    # have any meaningful effect.
    cmd = 'sudo tc qdisc add dev %s parent 1:1 handle 10:0 tbf rate 1000mbit buffer 1mbit limit 0.5mbit'%(dev)
    # TODO: haven't figured this out yet
    #print(cmd)
    #subprocess.check_call(cmd.split())
    
if __name__ == '__main__':
    go(sys.argv)
