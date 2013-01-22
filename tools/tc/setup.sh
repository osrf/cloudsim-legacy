#!/bin/bash

set -e

USAGE="USAGE: setup.sh <dev>
  E.g.: setup.sh eth0"

if [[ $# -ne 1 || $1 = '-h' ]]; then
  echo "$USAGE"
  exit 1
fi

IF=$1

set -x

# This script establishes tc (traffic control) rules that will be used to
# manipulate communication over a given interface.  The rules established
# by the script are meant to be no-ops; they don't affect communication now,
# but rather are meant to be modified later.  See configure.sh for an example
# of modification.

# Delete any existing rules
sudo tc qdisc del dev $IF root || true

# Now we'll add the rules we need, in a hierarchical fashion.  
# TODO: learn about the implications of the hierarchy and reconsider
# this particular order (which is patterned after the VRC Technical Guide
# Section 5.2)

# Add a rule to induce latency
sudo tc qdisc add dev $IF root handle 1:0 netem delay 0ms

# Add a rule to limit bandwidth.  We have to pick numbers here, so pick them high enough to not
# have any meaningful effect.
sudo tc qdisc add dev $IF parent 1:1 handle 10:0 tbf rate 1000mbit buffer 1mbit limit 0.5mbit

# Add a rule to drop packets
sudo tc qdisc add dev $IF parent 10:1 handle 20:0 netem loss 0.0%
