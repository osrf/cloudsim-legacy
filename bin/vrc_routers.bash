#!/bin/bash

# Execute a command (cmd), copy a file into /tmp (copy), or upload and run a
# script (script) in all the routers of the VRC. This tool can be combined with
# another script that uses vrc_ssh.py to copy files or run a command into the
# sim, fc1, or fc2.

USAGE="Usage: vrc_routers.sh <cmd|copy|script> <command|file>"
DEFAULT_CS=/home/ubuntu/cloudsim

if [ $# -ne 2 ]; then
  echo $USAGE
  exit 1
fi

OP=$1
ARG=$2

if [ "$OP" != "cmd" ] && [ "$OP" != "copy" ] && [ "$OP" != "script" ]; then
    echo $USAGE
    exit 1
fi

# Autocopy in all CloudSim JRs
./vrc_ssh.py copy vrc_ssh.py /home/ubuntu/cloudsim/bin cs

# Autocopy in all the Routers
./vrc_ssh.py run "sudo $DEFAULT_CS/bin/vrc_ssh.py copy $DEFAULT_CS/bin/vrc_ssh.py $DEFAULT_CS router" cs

if [ "$OP" == "copy" ] || [ "$OP" == "script" ]; then
    # Copy the file/script to upload/execute in all the CloudSims
    ./vrc_ssh.py copy $ARG /tmp cs

    # Copy the file/script to upload/execute in all the routers
    ./vrc_ssh.py run "sudo $DEFAULT_CS/bin/vrc_ssh.py copy /tmp/$ARG /tmp router" cs
fi

if [ "$OP" == "cmd" ]; then
    # Run a command in all the simulation machines
    ./vrc_ssh.py run "sudo $DEFAULT_CS/bin/vrc_ssh.py run $ARG router" cs

elif [ "$OP" == "script" ]; then
    # Run the script in all the remote machines
    ./vrc_ssh.py run "sudo $DEFAULT_CS/bin/vrc_ssh.py run /tmp/$ARG router" cs
fi
