from __future__ import print_function

import unittest
import os
import time
import zipfile
import shutil
import json
import subprocess
import dateutil.parser

from shutil import copyfile

from launch_utils.traffic_shaping import  run_tc_command


from launch_utils.monitoring import constellation_is_terminated,\
    monitor_launch_state,  monitor_ssh_ping,\
    monitor_task, monitor_simulator, TaskTimeOut

from launch_utils.softlayer import load_osrf_creds,\
    get_softlayer_path, get_machine_login_info, create_openvpn_key

from launch_utils.launch_db import get_constellation_data, ConstellationState,\
    get_cloudsim_config, log_msg

from launch_utils.testing import get_test_runner, get_test_path, get_boto_path,\
    get_test_dir
from launch_utils import get_unique_short_name
from launch_utils.startup_scripts import create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file,\
    create_ssh_connect_file

from launch_utils.sshclient import SshClient
from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue

import multiprocessing
from launch_utils.sl_cloud import acquire_softlayer_constellation,\
 terminate_softlayer_constellation

from launch_utils.aws import acquire_aws_constellation
from launch_utils.aws import terminate_aws_constellation


ROUTER_IP = '10.0.0.50'
SIM_IP = '10.0.0.51'
FC1_IP = '10.0.0.52'
FC2_IP = '10.0.0.53'
OPENVPN_SERVER_IP = '11.8.0.1'
OPENVPN_CLIENT_IP = '11.8.0.2'

launch_sequence = ["nothing", "launch", "os_reload", "init_router", "init_privates",
        "zip", "change_ip", "startup", "block_public_ips", "reboot", "running"]


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def update(constellation_name):
    """
    Update the constellation software on the servers.
    This function is a plugin function that should be implemented by
    each constellation type
    """

    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu',
                           router_ip)
    for state in ["sim_state", "router_state", "fc1_state", "fc2_state", ]:
        constellation.set_value(state, "packages_setup")
    try:
        pass
        o = ssh_router.cmd("cloudsim/update_constellation.bash")
        log("UPDATE: %s" % o, "toto")
    finally:
        for state in ["sim_state", "router_state", "fc1_state", "fc2_state", ]:
            constellation.set_value("sim_state", "running")
        log("UPDATE DONE", "toto")


def get_ping_data(ping_str):
    mini, avg, maxi, mdev = [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)


def start_simulator(constellation_name,
                    package_name,
                    launch_file_name,
                    launch_args,
                    task_timeout):
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    c = "bash cloudsim/start_sim.bash %s %s %s" % (package_name,
                                                   launch_file_name,
                                                   launch_args)
    cmd = c.strip()
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    r = ssh_router.cmd(cmd)
    log('start_simulator %s' % r)


def stop_simulator(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    r = ssh_router.cmd(cmd)
    log('stop_simulator %s' % r)


def start_task(constellation_name, task):

    log("** SIMULATOR *** start_task %s" % task)

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation_name,
                   'sim_machine_name',
                   'key-router',
                   'router_public_ip',
                   latency, up, down)

    log("** START SIMULATOR ***")
    start_simulator(constellation_name,
                    task['ros_package'],
                    task['ros_launch'],
                    task['ros_args'],
                    task['timeout'])


def stop_task(constellation, task):

    log("** CONSTELLATION %s *** STOP TASK %s ***" % (constellation,
                                                      task['task_id']))
    stop_simulator(constellation)

    log("** Notify portal ***")
    notify_portal(constellation, task)


def check_for_end_of_task(constellation_name, ssh_router):
    if monitor_task(constellation_name, ssh_router):
        raise TaskTimeOut()


def _get_ssh_router(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    return ssh_router


def ssh_ping_proc(constellation_name, ip, latency_key):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_ssh_ping(constellation_name, ssh_router, ip, latency_key)


def monitor_task_proc(constellation_name):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_task(constellation_name, ssh_router)


def monitor_simulator_proc(constellation_name):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_simulator(constellation_name, ssh_router, "sim_state")


def monitor(constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'init_router'):
        constellation_directory = constellation.get_value(
                                                    'constellation_directory')
        router_ip = constellation.get_value("router_public_ip")

        ssh_router = SshClient(constellation_directory,
                               "key-router",
                               'ubuntu',
                               router_ip)

        router_state = constellation.get_value('router_state')
        fc1_state = constellation.get_value('fc1_state')
        fc2_state = constellation.get_value('fc2_state')
        sim_state = constellation.get_value('sim_state')

        monitor_launch_state(constellation_name, ssh_router, router_state,
                          "tail -1 /var/log/dpkg.log", 'router_launch_msg')
        monitor_launch_state(constellation_name, ssh_router, fc1_state,
                            "cloudsim/dpkg_log_fc1.bash", 'fc1_launch_msg')
        monitor_launch_state(constellation_name, ssh_router, fc2_state,
                            "cloudsim/dpkg_log_fc2.bash", 'fc2_launch_msg')
        monitor_launch_state(constellation_name, ssh_router, sim_state,
                             "cloudsim/dpkg_log_sim.bash", 'sim_launch_msg')

        procs = []
        p = multiprocessing.Process(target=ssh_ping_proc,
                        args=(constellation_name, FC1_IP, 'fc1_latency'))
        procs.append(p)

        p = multiprocessing.Process(target=ssh_ping_proc,
                        args=(constellation_name, FC2_IP, 'fc2_latency'))
        procs.append(p)

        p = multiprocessing.Process(target=ssh_ping_proc,
                        args=(constellation_name, SIM_IP, 'sim_latency'))
        procs.append(p)

        p = multiprocessing.Process(target=ssh_ping_proc,
            args=(constellation_name, OPENVPN_CLIENT_IP, 'router_latency'))
        procs.append(p)

        p = multiprocessing.Process(target=monitor_task_proc,
                                    args=(constellation_name,))
        procs.append(p)
        p = multiprocessing.Process(target=monitor_simulator_proc,
                                    args=(constellation_name,))
        procs.append(p)

        for p in procs:
            p.start()

        for p in procs:
            p.join()

    return False


def _init_computer_data(constellation_name):

    constellation = ConstellationState(constellation_name)

    # init the redis db info
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")
    constellation.set_value("constellation_state", "launching")
    constellation.set_value("error", "")

    constellation.set_value("configuration_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")

    constellation.set_value("fc1_ip", FC1_IP)
    constellation.set_value("fc2_ip", FC2_IP)
    constellation.set_value("sim_ip", SIM_IP)
    constellation.set_value("router_ip", ROUTER_IP)

    constellation.set_value('fc1_launch_msg', 'nothing')
    constellation.set_value('fc2_launch_msg', 'nothing')
    constellation.set_value('sim_launch_msg', 'nothing')

    for prefix in ['router', 'sim', 'fc2', 'fc1']:
        constellation.set_value('%s_ip_address' % prefix, "nothing")
        constellation.set_value('%s_state' % prefix, "nothing")
        constellation.set_value('%s_aws_state' % prefix, 'pending')
        constellation.set_value('%s_launch_msg' % prefix, 'starting')
        constellation.set_value('%s_zip_file' % prefix, 'not ready')
        constellation.set_value('%s_latency' % prefix, '[]')
        constellation.set_value('%s_machine_name' % prefix,
                                '%s_%s' % (prefix, constellation_name))
        constellation.set_value('%s_key_name' % prefix, None)


def get_router_script(machine_private_ip, ros_master_ip, drc_package_name):

    s = """#!/bin/bash
# Exit on error
set -ex
exec >/home/ubuntu/launch_stdout_stderr.log 2>&1



cat <<DELIM > /etc/apt/sources.list


deb http://us.archive.ubuntu.com/ubuntu/ precise main restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ precise main restricted
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates main restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates main restricted
deb http://us.archive.ubuntu.com/ubuntu/ precise universe
deb-src http://us.archive.ubuntu.com/ubuntu/ precise universe
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates universe
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates universe
deb http://us.archive.ubuntu.com/ubuntu/ precise multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise multiverse
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates multiverse
deb http://us.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu precise-security main restricted
deb-src http://security.ubuntu.com/ubuntu precise-security main restricted
deb http://security.ubuntu.com/ubuntu precise-security universe
deb-src http://security.ubuntu.com/ubuntu precise-security universe
deb http://security.ubuntu.com/ubuntu precise-security multiverse
deb-src http://security.ubuntu.com/ubuntu precise-security multiverse
# deb http://archive.canonical.com/ubuntu precise partner
# deb-src http://archive.canonical.com/ubuntu precise partner
deb http://extras.ubuntu.com/ubuntu precise main
deb-src http://extras.ubuntu.com/ubuntu precise main


DELIM

# this is where we store all data for this part
mkdir -p /home/ubuntu/cloudsim
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

# Add OSRF repositories
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -

# ROS setup
sh -c 'echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list'
wget http://packages.ros.org/ros.key -O - | sudo apt-key add -

apt-get update

apt-get install -y ntp
apt-get install -y openvpn
apt-get install -y vim ipython

# SSH HPN
sudo apt-get install -y python-software-properties
sudo add-apt-repository -y ppa:w-rouesnel/openssh-hpn
sudo apt-get update
sudo apt-get install -y openssh-server

cat <<EOF >>/etc/ssh/sshd_config

# SSH HPN
HPNDisabled no
TcpRcvBufPoll yes
HPNBufferSize 8192
NoneEnabled yes
EOF

sudo service ssh restart

cat <<DELIM > /etc/openvpn/openvpn.conf
dev tun
ifconfig """ + OPENVPN_SERVER_IP + " " + OPENVPN_CLIENT_IP + """
secret static.key
DELIM


cat <<DELIM > /home/ubuntu/cloudsim/get_network_usage.bash
#!/bin/bash

#
# wall or sim clock, wall or sim clock, uplink downlink
# space is the separator
tail -1 /tmp/vrc_netwatcher_usage.log

DELIM
chmod +x /home/ubuntu/cloudsim/get_network_usage.bash


cat <<DELIM > /home/ubuntu/cloudsim/get_score.bash
#!/bin/bash

. /usr/share/drcsim/setup.sh
# rostopic echo the last message of the score
timeout -k 1 10 rostopic echo -p /vrc_score -n 1


DELIM
chmod +x /home/ubuntu/cloudsim/get_score.bash


# The openvpn key is generated
#openvpn --genkey --secret /home/ubuntu/cloudsim/openvpn.key
#cp /home/ubuntu/cloudsim/openvpn.key /etc/openvpn/static.key
#chmod 644 /etc/openvpn/static.key
#service openvpn restart


cat <<DELIM > /etc/init.d/iptables_cloudsim
#! /bin/sh




case "\$1" in
  start|"")

    sysctl -w net.ipv4.ip_forward=1
    #iptables -A FORWARD -i tun0 -o bond0 -j ACCEPT
    #iptables -A FORWARD -o tun0 -i bond0 -j ACCEPT
    iptables -t nat -A POSTROUTING -o bond1 -j MASQUERADE

    ;;
  stop)

       echo "N/A"
    ;;
  *)
    echo "Usage: iptables_cloudsim start|stop" >&2
    exit 3
    ;;
esac

:

DELIM

chmod +x  /etc/init.d/iptables_cloudsim
ln -sf /etc/init.d/iptables_cloudsim /etc/rc2.d/S99iptables_cloudsim

#invoke it
/etc/init.d/iptables_cloudsim start


# At least in some cases, we need to explicitly install graphviz before ROS to avoid apt-get dependency problems.
sudo apt-get install -y graphviz
# That could be removed if ros-comm becomes a dependency of cloudsim-client-tools
sudo apt-get install -y ros-fuerte-ros-comm
# We need atlas_msgs, which is in drcsim
sudo apt-get install -y """ + drc_package_name + """

# roscore is in simulator's machine
cat <<DELIM >> /etc/environment
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311
export ROS_IP=""" + machine_private_ip + """
source /usr/share/drcsim/setup.sh
DELIM

# Answer the postfix questions
sudo debconf-set-selections <<< "postfix postfix/mailname string `hostname`"
sudo debconf-set-selections <<< "postfix postfix/main_mailer_type string 'Internet Site'"

sudo apt-get install -y cloudsim-client-tools

sudo start vrc_monitor || true

# Create upstart vrc_sniffer job
cat <<DELIM > /etc/init/vrc_sniffer.conf
# /etc/init/vrc_sniffer.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_sniffer.py -t 11.8.0.2 -l vrc_current_outbound_latency > /var/log/vrc_sniffer.log 2>&1

respawn
DELIM

# Create upstart vrc_controller job for the private interface
cat <<DELIM > /etc/init/vrc_controller_private.conf
# /etc/init/vrc_controller_private.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -tl vrc_target_outbound_latency -s 0.5 -v -d bond0 > /var/log/vrc_controller_private.log 2>&1

respawn
DELIM

# Create upstart vrc_controller job for the public interface
cat <<DELIM > /etc/init/vrc_controller_public.conf
# /etc/init/vrc_controller_public.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -tl vrc_target_outbound_latency -s 0.5 -v -d bond1 > /var/log/vrc_controller_public.log 2>&1

respawn
DELIM

# Create upstart vrc_bytecounter job
cat <<DELIM > /etc/init/vrc_bytecounter.conf
# /etc/init/vrc_bytecounter.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero<caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_bytecounter bond0 > /var/log/vrc_bytecounter.log 2>&1

respawn
DELIM

# Create upstart vrc_netwatcher job
cat <<DELIM > /etc/init/vrc_netwatcher.conf
# /etc/init/vrc_netwatcher.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero<caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_wrapper.sh vrc_netwatcher.py -o -m replace -d /tmp -p vrc_netwatcher_usage > /var/log/vrc_netwatcher.log 2>&1

DELIM

# start vrc_sniffer and vrc_controllers
sudo start vrc_sniffer || true
sudo start vrc_controller_private || true
sudo start vrc_controller_public || true

# Don't start the bytecounter here; netwatcher will start it as needed
#start vrc_bytecounter

mkdir -p /home/ubuntu/cloudsim/setup
touch /home/ubuntu/cloudsim/setup/done
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

"""
    return s


def get_drc_script(drc_package_name, machine_ip, ros_master_ip,
                   gpu_driver_list, ppa_list):
    gpu_driver_packages_string = ""
    for driver in gpu_driver_list:
        gpu_driver_packages_string += "apt-get install -y %s\n" % driver

    ppa_string = ""
    for ppa in ppa_list:
        ppa_string += "apt-add-repository -y ppa:%s\n" % ppa

    s = """#!/bin/bash
# Exit on error
set -ex
# Redirect everybody's output to a file
logfile=/home/ubuntu/launch_stdout_stderr.log
exec > $logfile 2>&1


cat <<DELIM > /etc/apt/sources.list

deb http://us.archive.ubuntu.com/ubuntu/ precise main restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ precise main restricted
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates main restricted
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates main restricted
deb http://us.archive.ubuntu.com/ubuntu/ precise universe
deb-src http://us.archive.ubuntu.com/ubuntu/ precise universe
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates universe
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates universe
deb http://us.archive.ubuntu.com/ubuntu/ precise multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise multiverse
deb http://us.archive.ubuntu.com/ubuntu/ precise-updates multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-updates multiverse
deb http://us.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse
deb-src http://us.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu precise-security main restricted
deb-src http://security.ubuntu.com/ubuntu precise-security main restricted
deb http://security.ubuntu.com/ubuntu precise-security universe
deb-src http://security.ubuntu.com/ubuntu precise-security universe
deb http://security.ubuntu.com/ubuntu precise-security multiverse
deb-src http://security.ubuntu.com/ubuntu precise-security multiverse
# deb http://archive.canonical.com/ubuntu precise partner
# deb-src http://archive.canonical.com/ubuntu precise partner
deb http://extras.ubuntu.com/ubuntu precise main
deb-src http://extras.ubuntu.com/ubuntu precise main

DELIM

#
# we need python-software-properties for ad
# it requires apt-get update for some reason
#
apt-get remove -y unattended-upgrades

apt-get update
apt-get install -y python-software-properties zip
add-apt-repository -y ppa:w-rouesnel/openssh-hpn
apt-get update
apt-get install -y openssh-server

cat <<EOF >>/etc/ssh/sshd_config

# SSH HPN
HPNDisabled no
TcpRcvBufPoll yes
HPNBufferSize 8192
NoneEnabled yes
EOF

sudo service ssh restart

mkdir -p /home/ubuntu/cloudsim
mkdir -p /home/ubuntu/cloudsim/setup


cat <<DELIM > /etc/rc.local
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.

insmod /lib/modules/\`uname -r\`/kernel/drivers/net/ethernet/intel/ixgbe/ixgbe.ko

exit 0
DELIM





cat <<DELIM > /home/ubuntu/cloudsim/start_sim.bash
#!/bin/bash

MAX_TIME=30

# Remove the old logs
DIR=\`echo \$2 | cut -d'.' -f 1\`
rm -rf /tmp/\$DIR

echo \`date\` "\$1 \$2 \$3" >> /home/ubuntu/cloudsim/start_sim.log

. /usr/share/drcsim/setup.sh
if [ -f /home/ubuntu/local/share/vrc_arenas/setup.sh ]; then
 . /home/ubuntu/local/share/vrc_arenas/setup.sh
fi
export ROS_IP=""" + machine_ip + """
export GAZEBO_IP=""" + machine_ip + """
export DISPLAY=:0
ulimit -c unlimited
export GAZEBO_IP_WHITE_LIST=127.0.0.1

# Kill a pending simulation
bash /home/ubuntu/cloudsim/stop_sim.bash

roslaunch \$1 \$2 \$3 gzname:=gzserver  &

tstart=\$(date +%s)
timeout -k 1 5 gztopic list
while [[ \$? -ne 0 ]]; do
    tnow=\$(date +%s)
    if ((tnow-tstart>MAX_TIME)) ;then
        echo "[simulator start_sim.bash] Timed out waiting for simulation to start"
        exit 1
    fi

    sleep 1
    timeout -k 1 5 gztopic list
done

echo \`date\` "$1 $2 $3 - End" >> /home/ubuntu/cloudsim/start_sim.log

DELIM
chmod +x /home/ubuntu/cloudsim/start_sim.bash

cat <<DELIM > /home/ubuntu/cloudsim/stop_sim.bash
#!/bin/bash

MAX_TIME=30
echo \`date\` "Stop sim - Begin" >> /home/ubuntu/cloudsim/stop_sim.log
. /usr/share/drcsim/setup.sh

if timeout -k 1 2 gztopic list; then 
  LOG_PATH=\`ps aux | grep gzserver | grep -m 1 record_path | cut -d = -f 3 | cut -d ' ' -f 1\`/state.log
  echo "  Log file: \$LOG_PATH" >> /home/ubuntu/cloudsim/stop_sim.log 
  gzlog stop
  # Let cleanup start, which pauses the world
  sleep 5
  while [ "\`timeout -k 1 1 gzstats -p 2>/dev/null |cut -d , -f 4 | tail -n 1\`" != " F" ]; do
    sleep 1
    if [ "\`ps aux | grep gzserver | wc -l\`" == "1" ]; then
        echo "  gzserver died, force exit" >> /home/ubuntu/cloudsim/stop_sim.log
        break
    fi
    # look for the name of the Log file
    if [ "\`tail -n 1 \$LOG_PATH\`" = "</gazebo_log>" ] ; then 
        echo "  Log end tag detected" >> /home/ubuntu/cloudsim/stop_sim.log
        break
    fi
  done
fi
killall -INT roslaunch || true

tstart=\$(date +%s)
# Block until all ros process are killed
while [ "\`ps aux | grep ros | wc -l\`" != "1" ]; do

    tnow=\$(date +%s)
    if ((tnow-tstart>MAX_TIME)) ;then
        break
    fi

    sleep 1
done

# Kill all remaining ros processes
kill -9 \$(ps aux | grep ros | awk '{print \$2}') || true
killall -9 gzserver || true

DELIM
chmod +x /home/ubuntu/cloudsim/stop_sim.bash

cat <<DELIM > /home/ubuntu/cloudsim/ros.bash

# To connect via ROS:

# ROS's setup.sh will overwrite ROS_PACKAGE_PATH, so we'll first save the existing path
oldrpp=$ROS_PACKAGE_PATH

. /usr/share/drcsim/setup.sh
eval export ROS_PACKAGE_PATH=\$oldrpp:\\$ROS_PACKAGE_PATH
export ROS_IP=""" + machine_ip + """
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311

export GAZEBO_IP=""" + machine_ip + """
export GAZEBO_MASTER_URI=http://""" + ros_master_ip + """:11345

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/ping_gl.bash

DISPLAY=localhost:0 timeout 10 glxinfo

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/send_to_portal.bash
#!/bin/bash

# Create a zip file with the JSON task file, network usage and the sim log
# Then, the zip file is sent to the VRC portal

USAGE="Usage: send_to_portal <task_dirname> <zipname> <portal_key> <portal_url>"

if [ \$# -ne 4 ]; then
  echo \$USAGE
  exit 1
fi

TASK_DIRNAME=\$1
ZIPNAME=\$2
PORTAL_KEY=\$3
PORTAL_URL=\$4
LOG_DIR=/home/ubuntu/cloudsim/logs/\$TASK_DIRNAME
SIM_LOG_DIR=/tmp/\$TASK_DIRNAME
PORTAL_LOG_DIR=/home/ubuntu/cloudsim/logs/portal/\$TASK_DIRNAME

if [ ! -f $PORTAL_KEY ];
then
    echo VRC Portal key not found \$PORTAL_KEY
    exit 0
fi

mkdir -p \$PORTAL_LOG_DIR

# Create a zip file
zip -j \$PORTAL_LOG_DIR/\$ZIPNAME \$SIM_LOG_DIR/* \$LOG_DIR/* || true

if [ -f \$PORTAL_LOG_DIR/\$ZIPNAME ];
then
    # Send the zip file to the VRC Portal
    scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i \$PORTAL_KEY \$PORTAL_LOG_DIR/*.zip ubuntu@\$PORTAL_URL:/tmp

    ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i \$PORTAL_KEY ubuntu@\$PORTAL_URL sudo mv /tmp/\$ZIPNAME /vrc_logs/end_incoming
fi
DELIM


chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

# Add ROS and OSRF repositories
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

date >> /home/ubuntu/setup.log
echo 'setting up the ros and drc repos keys' >> /home/ubuntu/setup.log
wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -


""" + ppa_string + """

echo "update packages" >> /home/ubuntu/setup.log
apt-get update


cat <<DELIM > /etc/init.d/vpcroute
#! /bin/sh

case "\$1" in
  start|"")
        route del default
        route add """ + OPENVPN_CLIENT_IP + """ gw """ + ROUTER_IP + """
        route add default gw """ + ROUTER_IP + """
    ;;
  stop)
        route del """ + OPENVPN_CLIENT_IP + """ gw """ + ROUTER_IP + """

    ;;
  *)
    echo "Usage: vpcroute start|stop" >&2
    exit 3
    ;;
esac

:
DELIM

chmod +x  /etc/init.d/vpcroute
ln -sf /etc/init.d/vpcroute /etc/rc2.d/S99vpcroute

# invoke it now to add route to the router
/etc/init.d/vpcroute start || true

echo "install X, with nvidia drivers" >> /home/ubuntu/setup.log
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` gnome-session-fallback


""" + gpu_driver_packages_string + """

# Have the NVIDIA tools create the xorg configuration file for us, retrieiving the PCI BusID for the current system.
# The BusID can vary from machine to machine.  The || true at the end is to allow this line to succeed on fc2, which doesn't have a GPU.
if ! nvidia-xconfig --busid `nvidia-xconfig --query-gpu-info | grep BusID | head -n 1 | sed 's/PCI BusID : PCI:/PCI:/'`; then
  echo "nvidia-xconfig failed; probably no GPU installed.  Proceeding." >> /home/ubuntu/setup.log
else
  echo "nvidia-xconfig succeeded." >> /home/ubuntu/setup.log
fi

echo "setup auto xsession login" >> /home/ubuntu/setup.log

echo "
[SeatDefaults]
greeter-session=unity-greeter
autologin-user=ubuntu
autologin-user-timeout=0
user-session=gnome-fallback
" > /etc/lightdm/lightdm.conf
initctl stop lightdm || true
initctl start lightdm

#
# Install drc sim and related packages
#
apt-get install -y vim ipython
apt-get install -y ntp

echo "install """ + drc_package_name + """ ">> /home/ubuntu/setup.log
apt-get install -y """ + drc_package_name + """

echo "Updating bashrc file">> /home/ubuntu/setup.log

cat <<DELIM >> /home/ubuntu/.bashrc
# CloudSim
. /usr/share/drcsim/setup.sh
export DISPLAY=:0
export ROS_IP="""    + machine_ip + """
export GAZEBO_IP=""" + machine_ip + """

DELIM

echo "install cloudsim-client-tools" >> /home/ubuntu/setup.log
apt-get install -y cloudsim-client-tools


touch /home/ubuntu/cloudsim/setup/done

"""
    return s


def create_zip_file(zip_file_path, short_name, files_to_zip):

    with zipfile.ZipFile(zip_file_path, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(short_name, short_fname)
            fzip.write(fname, zip_name)


def create_private_machine_zip(machine_name_prefix,
                               machine_ip,
                               constellation_name,
                               constellation_directory,
                               key_prefix):

    machine_dir = os.path.join(constellation_directory, machine_name_prefix)
    os.makedirs(machine_dir)
    key_short_filename = '%s.pem' % key_prefix
    key_fpath = os.path.join(machine_dir, key_short_filename)
    copyfile(os.path.join(constellation_directory, key_short_filename),
             key_fpath)
    os.chmod(key_fpath, 0600)

    fname_ssh_sh = os.path.join(machine_dir,
                                'ssh-%s.bash' % machine_name_prefix)

    file_content = create_ssh_connect_file(key_short_filename, machine_ip)
    with open(fname_ssh_sh, 'w') as f:
        f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    files_to_zip = [key_fpath,
                    fname_ssh_sh, ]

    fname_zip = os.path.join(machine_dir, "%s_%s.zip" % (machine_name_prefix,
                                                         constellation_name))
    create_zip_file(fname_zip, "%s_%s" % (machine_name_prefix,
                                          constellation_name), files_to_zip)
    return fname_zip


def create_router_zip(router_ip, constellation_name, key_prefix,
                      constellation_directory):
    # create router zip file with keys
    # This file is kept on the server and provides the user with:
    #  - key file for ssh access to the router
    #  - openvpn key
    #  - scripts to connect with ssh, openvpn, ROS setup

    router_machine_dir = os.path.join(constellation_directory, "router")
    os.makedirs(router_machine_dir)

    # copy router-key into router directory
    router_key_short_filename = '%s.pem' % key_prefix  # 'key-router'
    router_key_path = os.path.join(router_machine_dir,
                                   router_key_short_filename)
    copyfile(os.path.join(constellation_directory, router_key_short_filename),
             router_key_path)
    os.chmod(router_key_path, 0600)

    vpn_key_short_filename = 'openvpn.key'
    vpnkey_fname = os.path.join(router_machine_dir, vpn_key_short_filename)
    copyfile(os.path.join(constellation_directory, vpn_key_short_filename),
             vpnkey_fname)
    os.chmod(vpnkey_fname, 0600)

    # create open vpn config file
    file_content = create_openvpn_client_cfg_file(router_ip,
                    client_ip=OPENVPN_CLIENT_IP, server_ip=OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(router_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)

    fname_start_vpn = os.path.join(router_machine_dir, "start_vpn.bash")
    file_content = create_vpc_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755)

    fname_ros = os.path.join(router_machine_dir, "ros.bash")
    file_content = create_ros_connect_file(machine_ip=OPENVPN_CLIENT_IP,
                                           master_ip=SIM_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)

    fname_ssh_sh = os.path.join(router_machine_dir, 'ssh-router.bash')
    file_content = create_ssh_connect_file(router_key_short_filename,
                                           router_ip)
    with open(fname_ssh_sh, 'w') as f:
        f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    # wait (if necessary) for openvpn key to have been generated
    #creating zip for admin and officer users
    files_to_zip = [router_key_path,
                    fname_start_vpn,
                    fname_ssh_sh,
                    fname_vpn_cfg,
                    vpnkey_fname,
                    fname_ros, ]
    router_fname_zip = os.path.join(router_machine_dir,
                                    "router_%s.zip" % constellation_name)
    create_zip_file(router_fname_zip,
                            "router_%s" % constellation_name, files_to_zip)

    # create another zip file, this time for users only
    # (without the ssh key or the ssh-router.bash)
    files_to_zip = [fname_start_vpn,
                    fname_vpn_cfg,
                    vpnkey_fname,
                    fname_ros, ]
    router_user_fname_zip = os.path.join(router_machine_dir,
                                    "user_router_%s.zip" % constellation_name)
    create_zip_file(router_user_fname_zip,
                                "router_%s" % constellation_name, files_to_zip)
    return router_fname_zip, router_user_fname_zip



def _create_zip_files(constellation_name,
                     constellation_directory,
                     machines):
    """
    Creates zip files for each machines. Different files are generated for
    user roles (ex: user_router.zip has no router ssh key)
    """
    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('zip'):
        return

    for machine_name, machine_data in machines.iteritems():
        machine_key_prefix = 'key-%s-%s' % (machine_name, constellation_name)
        msg_key = '%s_launch_msg' % machine_name
        zip_ready_key = "%s_zip_file" % machine_name
        zip_fname = os.path.join(constellation_directory,
                                 "%s.zip" % machine_name)
        zip_user_fname = os.path.join(constellation_directory,
                                 "user_%s.zip" % machine_name)

        constellation.set_value(msg_key, 'creating zip file')
        if machine_name == "router":
            router_ip = constellation.get_value("router_public_ip")
            router_zip_fname, router_zip_user_fname = create_router_zip(
                                                    router_ip,
                                                    constellation_name,
                                                    machine_key_prefix,
                                                    constellation_directory)
            shutil.copy(router_zip_fname, zip_fname)
            shutil.copy(router_zip_user_fname, zip_user_fname)
        else:
            constellation.set_value(msg_key, 'creating zip files')
            ip = machine_data['ip']
            machine_zip_fname = create_private_machine_zip(machine_name,
                                               ip,
                                               constellation_name,
                                               constellation_directory,
                                               machine_key_prefix)
            shutil.copy(machine_zip_fname, zip_fname)
            if machine_name != "sim":
                shutil.copy(machine_zip_fname, zip_user_fname)
        constellation.set_value(zip_ready_key, 'ready')

    constellation.set_value("launch_stage", "zip")


def _reboot_machines(constellation_name,
                     ssh_router,
                    machine_names,
                    constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('reboot'):
        return

    #constellation.set_value('router_aws_state', m)
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       "cloudsim/setup/done",
                       "running")

    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name,
                                    "Rebooting after software installation")
        constellation.set_value('%s_aws_state' % machine_name, "rebooting")

    for machine_name in machine_names:
        ssh_router.cmd("cloudsim/reboot_%s.bash" % machine_name)
    constellation.set_value("launch_stage", "reboot")


def _run_machines(constellation_name, machine_names, constellation_directory):

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       "cloudsim/setup/done",
                       "running")

    constellation = ConstellationState(constellation_name)
    if "sim" in machine_names:
        constellation.set_value('sim_launch_msg', 'Testing X and OpenGL')
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory,
                               "key-router",
                               'ubuntu',
                               router_ip)
        constellation.set_value('simulation_glx_state', "pending")
        gl_retries = 0
        while True:
            gl_retries += 1
            time.sleep(10)
            try:
                ping_gl = ssh_router.cmd("bash cloudsim/ping_gl.bash")
                log("bash cloudsim/ping_gl.bash = %s" % ping_gl)
                constellation.set_value('simulation_glx_state', "running")
                break
            except Exception, e:
                if gl_retries > 30:
                    constellation.set_value('simulation_glx_state',
                                            "not running")
                    constellation.set_value('error',
                                            "OpenGL diagnostic failed: %s" % e)
                    raise
        # Install gazebo models locally
        # using a utility script from cloudsim-client-tools
        # careful, we are running as root here?
        constellation.set_value('sim_launch_msg', 'Loading Gazebo models')
        ssh_router.cmd("cloudsim/set_vrc_private.bash")

    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name, "Complete")
        constellation.set_value('%s_aws_state' % machine_name, "running")
        constellation.set_value('%s_launch_state' % machine_name, "running")
    constellation.set_value("launch_stage", "running")


def launch(username, config, constellation_name, tags,
           constellation_directory, credentials_override=None):
    """
    Called by cloudsimd when it receives a launch message
    """

    log("launch constellation name: %s" % constellation_name)

    constellation = ConstellationState(constellation_name)
    constellation.set_value("launch_stage", "launch")

    drcsim_package_name = "drcsim"
    ppa_list = []  # ['ubuntu-x-swat/x-updates']
    gpu_driver_list = ['nvidia-current',
                       'nvidia-settings',
                       'nvidia-current-dev']
    # if true, the machines are reloaded. This is done in the case
    # of partial reload because the terminate button would wipe out
    # all machines

#     partial_deploy = False
#     if config.find("partial") > 0:
#         partial_deploy = True

    if config.find("nightly") >= 0:
        drcsim_package_name = "drcsim-nightly"
    elif config.find("nvidia 319") >= 0:
        ppa_list = ['xorg-edgers/ppa']
        gpu_driver_list = ["nvidia-319", 'nvidia-settings']

    log("DRC package %s" % drcsim_package_name)
    log("ppas: %s" % ppa_list)
    log("gpu packages %s" % gpu_driver_list)

    _init_computer_data(constellation_name)
#         terminate_softlayer_constellation(constellation_name,
#                            constellation_prefix,
#                            partial_deploy,
#                            credentials_softlayer)
    ros_master_ip = SIM_IP
    router_script = get_router_script(ROUTER_IP, SIM_IP, drcsim_package_name)
    sim_script = get_drc_script(drcsim_package_name,
                                SIM_IP,
                                ros_master_ip,
                                gpu_driver_list,
                                ppa_list)

    fc1_script = get_drc_script(drcsim_package_name,
                                    FC1_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list)

    fc2_script = get_drc_script(drcsim_package_name,
                                    FC2_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list)

    machines = {'router': {'hardware': 't1.micro',
                      'software': 'ubuntu_1204_x64',
                      'ip': ROUTER_IP,
                      'startup_script': router_script},
            'sim': {'hardware': 'cg1.4xlarge',
                  'software': 'ubuntu_1204_x64_cluster',
                  'ip': SIM_IP,
                  'startup_script': sim_script},
#             'fc1': {'hardware': 'cg1.4xlarge',
#                   'software': 'ubuntu_1204_x64_cluster',
#                   'ip': FC1_IP,
#                   'startup_script': fc1_script},
#             'fc2': {'hardware': 'cg1.4xlarge',
#                   'software': 'ubuntu_1204_x64_cluster',
#                   'ip': FC2_IP,
#                   'startup_script': fc2_script}
            }
    cs_cfg = get_cloudsim_config()
    if "OSRF" in constellation_name:
        credentials_fname = cs_cfg['softlayer_path']
        if credentials_override:
            credentials_fname = credentials_override
        log("softlayer %s" % credentials_fname)
        constellation_prefix = config.split()[-1]
        log("constellation_prefix %s" % constellation_prefix)
        partial_deploy = False
        if config.find("partial") > 0:
            partial_deploy = True
        log("partial deploy: %s (only sim and router)" % partial_deploy)
        acquire_softlayer_constellation(constellation_name,
                                    constellation_directory,
                                    partial_deploy,
                                    constellation_prefix,
                                    credentials_fname,
                                    tags,
                                    router_script,
                                    sim_script,
                                    fc1_script,
                                    fc2_script)

    else:
        credentials_fname = cs_cfg['boto_path']
        if credentials_override:
            credentials_fname = credentials_override
        log("credentials_ec2 %s" % credentials_fname)
        acquire_aws_constellation(constellation_name,
                                  credentials_fname,
                                  machines,
                                  tags)

    router_ip = constellation.get_value('router_public_ip')
    router_key_pair_name = constellation.get_value("router_key_pair_name")
    ssh_router = SshClient(constellation_directory,
                            router_key_pair_name,
                            'ubuntu',
                            router_ip)

    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname)

    _create_zip_files(constellation_name, constellation_directory, machines)

        #constellation.set_value('router_aws_state', m)
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machines.keys(),
                       "cloudsim/setup/done",
                       "running")

    constellation.set_value('router_launch_msg', "vpn server setup")
    remote_fname = 'openvpn.key'
    ssh_router.upload_file(openvpn_fname, remote_fname)
    ssh_router.cmd('sudo cp openvpn.key /etc/openvpn/static.key; '
                   'sudo chmod 644 /etc/openvpn/static.key; '
                   'sudo service openvpn restart')

    # reboot fc1, fc2 and sim (but not router)
    machines_to_reboot = machines.keys()
    machines_to_reboot.remove('router')
    _reboot_machines(constellation_name,
                     ssh_router,
                     machines_to_reboot,
                     constellation_directory)

    # wait for all machines to be ready
    _run_machines(constellation_name, machines.keys(), constellation_directory)


def terminate(constellation_name, credentials_override=None):
    constellation = ConstellationState(constellation_name)
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('router_state', 'terminating')
    constellation.set_value('sim_state', 'terminating')
    constellation.set_value('field1_state', 'terminating')
    constellation.set_value('field2_state', 'terminating')
    constellation.set_value('sim_glx_state', "not running")
    constellation.set_value('sim_launch_msg', "terminating")
    constellation.set_value('router_launch_msg', "terminating")
    constellation.set_value('field1_launch_msg', "terminating")
    constellation.set_value('field2_launch_msg', "terminating")

    cs_cfg = get_cloudsim_config()
    constellation.set_value("launch_stage", "nothing")

    if not "OSRF" in constellation_name:
        credentials_fname = cs_cfg['boto_path']
        if credentials_override:
            credentials_fname = credentials_override
        terminate_aws_constellation(constellation_name, credentials_fname)
    else:
        credentials_fname = cs_cfg['boto_path']
        if credentials_override:
            credentials_fname = credentials_override
        partial = False
        constellation_prefix = constellation_name.split('_')[-1]
        terminate_softlayer_constellation(constellation_name,
                       constellation_prefix,
                       partial,
                       credentials_fname)

    constellation.set_value('sim_state', 'terminated')
    constellation.set_value('sim_launch_msg', "terminated")
    constellation.set_value('router_state', 'terminated')
    constellation.set_value('router_launch_msg', "terminated")
    constellation.set_value('field1_state', 'terminated')
    constellation.set_value('field1_launch_msg', "terminated")
    constellation.set_value('field2_state', 'terminated')
    constellation.set_value('field2_launch_msg', "terminated")
    constellation.set_value('constellation_state', 'terminated')


def __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       ls_cmd,
                       end_state):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return

    router_ip = constellation.get_value("router_public_ip")
    router_key_name = constellation.get_value("router_key_pair_name")
    ssh_router = SshClient(constellation_directory,
                           router_key_name,
                           'ubuntu',
                           router_ip)
    q = []
    for machine_name in machine_names:
        q.append(get_ssh_cmd_generator(ssh_router,
                                        "ls %s" % ls_cmd,
                                        ls_cmd,
                                        constellation,
                                        "%s_state" % machine_name,
                                        "running",
                                        max_retries=500))
    empty_ssh_queue(q, sleep=2)


def notify_portal(constellation, task):
    try:
        root_log_dir = '/tmp/cloudsim_logs'

        # Get metadata (team, competition, ...)
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        log("** Portal JSON path: %s ***" % portal_info_fname)
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        log("** Portal JSON file opened ***")
        team = portal_info['team']
        comp = portal_info['event']
        task_num = task['vrc_num']

        log("** Team: %s, Event: %s ***" % (team, comp))

        if task_num < '1' or task_num > '3':
            task_num = '1'
        run = task['vrc_id']
        if run < '1' or run > '5':
            run = '1'

        start_time = task['start_time']
        start_task = dateutil.parser.parse(start_time)
        start_task = start_task.strftime("%d/%m/%y %H:%M:%S")

        const = ConstellationState(constellation)
        constellation_dict = get_constellation_data(constellation)
        constellation_directory = constellation_dict['constellation_directory']
        router_ip = const.get_value("router_public_ip")

        task_id = task['ros_launch']
        task_dirname = task_id.split('.')[0]

        # Store in this cloudsim the network and sim logs
        router_key = os.path.join(constellation_directory, 'key-router.pem')

        new_msg = task['task_message'] + '<B> Getting logs</B>'
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        cmd = ('bash /var/www/bin/get_logs.bash %s %s %s'
               % (task_dirname, router_ip, router_key))
        subprocess.check_call(cmd.split())
        log("** Log directory created***")

        # Get the score and falls
        score = '0'
        #falls = 'N/A'
        runtime = 'N/A'
        try:
            p = os.path.join(root_log_dir, task_dirname, 'score.log')
            with open(p) as f:
                log("** score.log found **")
                data = f.read()
                log("** Reading score.log file **")
                lines = data.split('\n')
                last_line = lines[-2]
                log("** Last line: %s **" % last_line)
                score = last_line.split(',')[4]
                #falls = last_line.split(',')[5]

                # Time when the task stopped
                runtime = last_line.split(',')[1]
                log("** All sim score fields parsed **")
        except Exception:
            None

        # Create JSON file with the task metadata
        data = json.dumps({'team': team, 'event': comp, 'task': task_num,
                           'start_time': start_task, 'result': 'Terminated',
                           'runtime': runtime, 'score': score},
                          sort_keys=True, indent=4, separators=(',', ': '))

        log("** JSON data created **")
        with open(os.path.join(root_log_dir, task_dirname,
                               'end_task.json'), 'w') as f:
            f.write(str(data))

        log("** JSON file created ***")

        new_msg = new_msg.replace('Getting logs', 'Creating tar file')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Tar all the log content
        tar_name = (team + '_' + comp + '_' + str(task_num) + '_' + str(run) +
                    '.tar')
        p = os.path.join(root_log_dir, task_dirname)
        cmd = 'tar cf /tmp/' + tar_name + ' -C ' + p + ' .'
        subprocess.check_call(cmd.split())

        log("** Log directory stored in a tar file ***")

        new_msg = new_msg.replace('Creating tar file',
                                  'Uploading logs to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Send the log to the portal
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        ssh_portal = SshClient('xxx', 'xxx', portal_info['user'],
                               portal_info['hostname'])
        # this is a hack
        ssh_portal.key_fname = config['cloudsim_portal_key_path']

        # Upload the file to the Portal temp dir
        dest = os.path.join('/tmp', tar_name)

        cmd = ('scp -o UserKnownHostsFile=/dev/null'
               '-o StrictHostKeyChecking=no'
               ' -i ' + ssh_portal.key_fname + ' ' + dest + ' ubuntu@' +
               portal_info['hostname'] + ':/tmp')
        log('cmd: %s' % cmd)
        subprocess.check_call(cmd.split())

        # Move the file to the final destination into the Portal
        final_dest = os.path.join(portal_info['final_destination_dir'],
                                  tar_name)
        cmd = 'sudo mv %s %s' % (dest, final_dest)
        ssh_portal.cmd(cmd)

        new_msg = new_msg.replace('Uploading logs to the portal',
                                  'Logs uploaded to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

    except Exception, excep:
        log('notify_portal() Exception: %s' % (repr(excep)))
        raise


class MonitorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxb49a97c4'
        cred = get_softlayer_path()

        monitor(user, const, cred)


class VrcCase(object):  # (unittest.TestCase):

    def atest_zip_create(self):
        constellation_name = "toto"
        constellation_directory = os.path.join(get_test_path("zip_test"))
        router_ip = '50.23.225.173'
        create_router_zip(router_ip,
                          constellation_name,
                          constellation_directory)
        create_private_machine_zip("fc1",
                                     FC1_IP,
                                     constellation_name,
                                     constellation_directory)

#     def test_script(self):
#         s = get_sim_script('drcsim')
#         print(s)
#         print("")

    def atest_launch(self):

        constellation_prefix = "02"
        #launch_stage = None  # use the current stage

        #launch_stage = "nothing"
        #launch_stage = "os_reload"
        # "nothing", "os_reload", "init_router", "init_privates", "zip",
        # "change_ip", "startup", "reboot", "running"
        launch_stage = "running"

        self.constellation_name = 'test_vrc_contest_%s' % constellation_prefix
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer = get_softlayer_path()
        CONFIGURATION = 'vrc_contest'
        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name = get_unique_short_name(test_name + "_")
            P = os.path.join(get_test_path(test_name), self.constellation_name)
            self.constellation_directory = os.path.abspath(P)
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            p = os.path.join(get_test_path(test_name), self.constellation_name)
            self.constellation_directory = os.path.abspath(p)

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory",
                                    self.constellation_directory)
        constellation.set_value("configuration", 'vrc_contest')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        self.tags = {'TestCase': CONFIGURATION,
                     'configuration': CONFIGURATION,
                     'constellation': self.constellation_name,
                     'user': self.username,
                     'GMT': "now"}

        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)
        config = "OSRF VRC Constellation %s" % constellation_prefix

        launch(self.username,
               config,
               self.constellation_name,
               self.tags,
               self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.username, self.constellation_name, i)
            time.sleep(1)

        terminate(self.constellation_name, self.credentials_softlayer)

    def atest_monitor(self):

        self.constellation_name = "cxf44f7040"
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer = get_softlayer_path()

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.username, self.constellation_name, i)
            time.sleep(1)

    def stest_ubuntu_user_on_sim_from_router(self):

        constellation = ConstellationState('test_vrc_contest_toto')

        constellation_directory = constellation.get_value(
                                                    "constellation_directory")
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory,
                               "key-router",
                               'ubuntu',
                               router_ip)
        credentials_softlayer = get_softlayer_path()
        osrf_creds = load_osrf_creds(credentials_softlayer)

        pub_ip, ip, password = get_machine_login_info(osrf_creds, "sim-01")
        log("setting up ubuntu user on simulator machine "
            "[%s / %s]" % (pub_ip, ip))
        cmd = ("cd cloudsim; ./auto_ubuntu.bash "
            "%s %s ./key-sim.pem.pub" % (ip, password))
        log(cmd)
        out = ssh_router.cmd(cmd)
        log(out)

    def tearDown(self):
        unittest.TestCase.tearDown(self)


class AwsCase(unittest.TestCase):

    def setUp(self):
        print("setup")

        self.constellation_name = "test_xxx"
        print(self.constellation_name)

        self.config = "AWS trio"
        self.username = "test@osrfoundation.org"

        print("%s %s" % (self.config, self.constellation_name))

        self.constellation_directory = os.path.join(get_test_dir(),
                                               self.constellation_name)
        print(self.constellation_directory)

        if os.path.exists(self.constellation_directory):
            bk_name = self.constellation_directory + get_unique_short_name('_')
            os.rename(self.constellation_directory, bk_name)
        os.makedirs(self.constellation_directory)

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_directory",
                                self.constellation_directory)

        constellation.set_value('username', self.username)
        constellation.set_value('constellation_name', self.constellation_name)
        constellation.set_value('gmt', 'gmt')
        constellation.set_value('configuration', self.config)
        constellation.set_value('constellation_directory',
                                self.constellation_directory)
        constellation.set_value('error', '')

        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

    def test_it(self):
        print("test_launch")
        tags = {}
        p = get_boto_path()
        launch(self.username,
               self. config,
               self.constellation_name,
               tags,
               self.constellation_directory,
               credentials_override=p)
        print("launched")

        for i in range(20):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

        constellation = ConstellationState(self.constellation_name)
        self.assert_(constellation.get_value('gazebo') == "not running", "!")

        task = {}
        task['latency'] = 0
        task['uplink_data_cap'] = 0
        task['downlink_data_cap'] = 0
        task['ros_package'] = "atlas_utils"
        task['ros_launch'] = "vrc_task_1.launch"
        task['ros_args'] = ""
        task['timeout'] = 60

        start_task(self.constellation_name, task)

        for i in range(3):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

        self.assert_(constellation.get_value('gazebo') == "running", "!")

        for i in range(20):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

    def tearDown(self):
        print("teardown")
        terminate(self.constellation_name,
                  credentials_override=get_boto_path())
        constellation = ConstellationState(self.constellation_name)
        constellation.set_value('constellation_state', 'terminated')
        log("Deleting %s from the database" % self.constellation_name)
        constellation.expire(1)

if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
