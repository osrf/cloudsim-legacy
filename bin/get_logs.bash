#!/bin/bash

# Get simulator and network logs from the router

USAGE="Usage: get_logs.bash <task_dirname> <public_router_IP> <router_key>"

if [ $# -ne 3 ]; then
  echo $USAGE
  exit 1
fi

TASK_DIRNAME=$1
ROUTER_IP=$2
ROUTER_KEY=$3

mkdir -p /tmp/cloudsim_logs/$TASK_DIRNAME
sudo ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $ROUTER_KEY ubuntu@$ROUTER_IP bash /home/ubuntu/cloudsim/get_sim_logs.bash $TASK_DIRNAME

sudo scp -r -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $ROUTER_KEY ubuntu@$ROUTER_IP:/home/ubuntu/cloudsim/logs/$TASK_DIRNAME/* /tmp/cloudsim_logs/$TASK_DIRNAME || true
