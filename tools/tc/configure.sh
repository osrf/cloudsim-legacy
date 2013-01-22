#!/bin/bash

set -e

USAGE="configure.sh <dev> <latency> <bandwidth> <loss>
  E.g.: configure.sh eth0 100ms 125 0.1%"

if [[ $# -ne 4 || $1 = '-h' ]]; then
  echo "$USAGE"
  exit 1
fi

IF=$1
LATENCY=$2
BANDWIDTH=$3
LOSS=$4

set -x

# Add a rule to induce latency
sudo tc qdisc change dev $IF root handle 1:0 netem delay $LATENCY

# Add a rule to limit bandwidth
# A rule of thumb (http://opalsoft.net/qos/DS-24.htm) seems to be that:
#  buffer >= 0.001 * rate
#  limit ~= 0.5 * buffer
# TODO: look into those numbers more thoroughly
# 
# Separate the number and unit in the rate so that we can do math on it (why am I doing this in bash?)
# TODO: this doesn't seem to work correctly as tc doesn't accept units on all params (I think)
BANDWIDTH_NUMERICAL=`echo $BANDWIDTH | sed 's/\([0-9]*\).*/\1/'`
BANDWIDTH_UNIT=`echo $BANDWIDTH | sed 's/[0-9]*\(.*\)/\1/'`
BUFFER_NUMERICAL=`echo "$BANDWIDTH_NUMERICAL * 0.001" | bc -q`
LIMIT_NUMERICAL=`echo "$BUFFER_NUMERICAL * 0.5" | bc -q`
sudo tc qdisc change dev $IF parent 1:1 handle 10:0 tbf rate ${BANDWIDTH_NUMERICAL}${BANDWIDTH_UNIT} buffer ${BUFFER_NUMERICAL}${BANDWIDTH_UNIT} limit ${LIMIT_NUMERICAL}${BANDWIDTH_UNIT}

# Add a rule to drop packets
sudo tc qdisc change dev $IF parent 10:1 handle 20:0 netem loss 0.0%

