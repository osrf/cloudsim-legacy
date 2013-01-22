#!/bin/bash

# Add a rule to induce latency
tc qdisc add dev eth0 root handle 1:0 netem delay 100ms
