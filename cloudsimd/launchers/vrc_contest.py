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

from launch_utils.traffic_shapping import  run_tc_command

import launch_utils.softlayer

from launch_utils.monitoring import constellation_is_terminated,\
    monitor_launch_state,  monitor_ssh_ping,\
    monitor_task, monitor_simulator, TaskTimeOut

from launch_utils.softlayer import load_osrf_creds, reload_servers,\
    get_softlayer_path, wait_for_server_reloads, get_machine_login_info,\
    setup_ssh_key_access, create_ssh_key, create_openvpn_key,\
    shutdown_public_ips, enable_public_ips, get_active_transaction

from launch_utils.launch_db import get_constellation_data, ConstellationState,\
    get_cloudsim_config, log_msg

from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.launch import get_unique_short_name
from launch_utils.startup_scripts import create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file,\
    create_ssh_connect_file

from launch_utils.sshclient import SshClient, clean_local_ssh_key_entry
from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue

import multiprocessing


ROUTER_IP = '10.0.0.50'
SIM_IP = '10.0.0.51'
FC1_IP = '10.0.0.52'
FC2_IP = '10.0.0.53'
OPENVPN_SERVER_IP = '11.8.0.1'
OPENVPN_CLIENT_IP = '11.8.0.2'

launch_sequence = ["nothing", "os_reload", "init_router", "init_privates",
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
    for state in ["sim_state", "router_state", "fc1_state", "fc2_state",]:
        constellation.set_value(state, "packages_setup")
    try:
        pass
        o = ssh_router.cmd("cloudsim/update_constellation.bash")
        log("UPDATE: %s" % o, "toto")
    finally:
        for state in ["sim_state", "router_state", "fc1_state", "fc2_state",]:
            constellation.set_value("sim_state", "running")
        log("UPDATE DONE", "toto")


def get_ping_data(ping_str):
    mini, avg, maxi, mdev = [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)


def start_simulator(constellation_name, package_name, launch_file_name, launch_args, task_timeout):
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    c = "bash cloudsim/start_sim.bash %s %s %s" % (package_name, launch_file_name, launch_args)
    cmd = c.strip()
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    r = ssh_router.cmd(cmd)
    log('start_simulator %s' % r)


def stop_simulator(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    r = ssh_router.cmd(cmd)
    log('stop_simulator %s' % r)


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
            with open(os.path.join(root_log_dir, task_dirname, 'score.log')) as f:
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
        cmd = 'tar cf /tmp/' + tar_name + ' -C ' + os.path.join(root_log_dir, task_dirname) + ' .'
        subprocess.check_call(cmd.split())

        log("** Log directory stored in a tar file ***")

        new_msg = new_msg.replace('Creating tar file', 'Uploading logs to the portal')
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
        #ssh_portal.upload_file(portal_info_fname, dest)
        cmd = ('scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'
               ' -i ' + ssh_portal.key_fname + ' ' + dest + ' ubuntu@' +
               portal_info['hostname'] + ':/tmp')
        log('cmd: %s' % cmd)
        subprocess.check_call(cmd.split())

        # Move the file to the final destination into the Portal
        final_dest = os.path.join(portal_info['final_destination_dir'],
                                  tar_name)
        cmd = 'sudo mv %s %s' % (dest, final_dest)
        ssh_portal.cmd(cmd)

        new_msg = new_msg.replace('Uploading logs to the portal', 'Logs uploaded to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

    except Exception, excep:
        log ('notify_portal() Exception: %s' % (repr(excep)))
        raise


def start_task(constellation, task):

    log("** SIMULATOR *** start_task %s" % task)

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation, 'sim_machine_name', 'key-router', 'router_public_ip', latency, up, down)

    log("** START SIMULATOR ***")
    start_simulator(constellation, task['ros_package'], task['ros_launch'], task['ros_args'], task['timeout'])


def stop_task(constellation, task):

    log("** CONSTELLATION %s *** STOP TASK %s ***" % (constellation, task['task_id']))
    stop_simulator(constellation)

    log("** Notify portal ***")
    notify_portal(constellation, task)


def check_for_end_of_task(constellation_name, ssh_router):
    if monitor_task(constellation_name, ssh_router):
        raise TaskTimeOut()



def _get_ssh_router(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value('constellation_directory')
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
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


def monitor(username, constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init_router'):
        constellation_directory = constellation.get_value('constellation_directory')
        router_ip = constellation.get_value("router_public_ip")

        ssh_router = SshClient(constellation_directory, "key-router",
                               'ubuntu', router_ip)

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

        #monitor_ssh_ping(constellation_name, ssh_router, OPENVPN_CLIENT_IP, 'router_latency')
        #monitor_task(constellation_name, ssh_router)
        #monitor_simulator(constellation_name, ssh_router, "sim_state")

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
        constellation.set_value('%s_machine_name' % prefix, '%s_%s' % (prefix, constellation_name))
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

#
# The openvpn key is generated in CloudSim

#
cp /home/ubuntu/cloudsim/openvpn.key /etc/openvpn/static.key
chmod 644 /etc/openvpn/static.key

service openvpn restart


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


"""+ ppa_string +"""

echo "update packages" >> /home/ubuntu/setup.log
apt-get update


cat <<DELIM > /etc/init.d/vpcroute
#! /bin/sh

case "\$1" in
  start|"")
        route del default
        route add """ + OPENVPN_CLIENT_IP+""" gw """ + ROUTER_IP+"""
        route add default gw """ + ROUTER_IP+"""
    ;;
  stop)
        route del """ + OPENVPN_CLIENT_IP+""" gw """ + ROUTER_IP+"""

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


class ReloadOsCallBack(object):
    def __init__(self, constellation_name, machines_dict):
        self.constellation_name = constellation_name
        self.machines_dict = machines_dict
        self.constellation_state = ConstellationState(constellation_name)

    def callback(self, machine_name, state):
        msg_key = self.machines_dict[machine_name]
        log("[%s] %s [%s] %s" % (self.constellation_name,
                                 machine_name, msg_key, state))

        self.constellation_state.set_value(msg_key, state)


def _reload_os_machines(constellation_name,
                       constellation_prefix,
                       partial_reload,
                       osrf_creds_fname):

    constellation = ConstellationState(constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('os_reload'):
        return
    else:
        osrf_creds = load_osrf_creds(osrf_creds_fname)
        # compute the softlayer machine names
        constellation.set_value('sim_launch_msg', 'reload OS')
        machine_names = [x + "-" + constellation_prefix for x in ('router',
                                                                  'sim')]
        if not partial_reload:
            machine_names.append('fc2-' + constellation_prefix)
            machine_names.append('fc1-' + constellation_prefix)
            constellation.set_value('fc1_launch_msg', 'reload OS')
            constellation.set_value('fc2_launch_msg', 'reload OS')
        # enable nics on machines with disconnected ones (not the router)
        enable_public_ips(osrf_creds, machine_names[1:])
        for server in machine_names[1:]:
            t = get_active_transaction(osrf_creds, server)
            log("Transaction before reload on %s: %s" % (server, t))
        reload_servers(osrf_creds, machine_names)
        constellation.set_value("launch_stage", "os_reload")


def __add_ubuntu_user_to_router(router_ip, password,
                              constellation_directory,
                              key_prefix='key-router'):

    clean_local_ssh_key_entry(router_ip)
    create_ssh_key(key_prefix, constellation_directory)
    # setup a ubuntu sudoer no password user with an ssh key
    router_pub_key_path = os.path.join(constellation_directory,
                                       "%s.pem.pub" % key_prefix)
    setup_ssh_key_access(router_ip, password, router_pub_key_path)
    router_priv_key_path = os.path.join(constellation_directory,
                                        "%s.pem" % key_prefix)
    log("ssh -i %s ubuntu@%s" % (router_priv_key_path, router_ip))


def __upload_ssh_keys_to_router(ssh_router,
                              machine_prefix,
                              constellation_directory):
    # upload public key to router
    local_fname = os.path.join(constellation_directory,
                               'key-%s.pem.pub' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem.pub' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload public key %s to %s" % (local_fname, remote_fname))

    # upload private key to router
    local_fname = os.path.join(constellation_directory,
                               'key-%s.pem' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload private key %s to %s" % (local_fname, remote_fname))


def _wait_for_constellation_reload(constellation_name,
                                  constellation_prefix,
                                  partial_deploy,
                                  osrf_creds_fname):

    machines_dict = {}
    machines_dict['sim-%s' % constellation_prefix] = 'sim_launch_msg'
    machines_dict['router-%s' % constellation_prefix] = 'router_launch_msg'
    if not partial_deploy:
        machines_dict['fc2-%s' % constellation_prefix] = 'fc2_launch_msg'
        machines_dict['fc1-%s' % constellation_prefix] = 'fc1_launch_msg'

    log("machines_dict %s" % machines_dict)
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
    wait_for_server_reloads(osrf_creds, machines_dict.keys(),
                            reload_monitor.callback)


def _initialize_router(constellation_name,
                      constellation_prefix,
                      partial_deploy,
                      osrf_creds_fname,
                      constellation_directory):

    constellation = ConstellationState(constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'init_router'):
        return

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    router_name = "router-%s" % constellation_prefix

    m = "running"
    constellation.set_value('fc1_aws_state', m)
    constellation.set_value('fc2_aws_state', m)
    constellation.set_value('sim_aws_state', m)
    constellation.set_value('router_aws_state', m)

    constellation.set_value('router_launch_msg', 'user account setup')
    router_ip, priv_ip, password = get_machine_login_info(osrf_creds,
                                                          router_name)
    constellation.set_value("router_public_ip", router_ip)
    log("router %s %s" % (router_ip, password))

    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(
                                osrf_creds, "sim-%s" % constellation_prefix)
    log("sim %s %s" % (sim_pub_ip, sim_root_password))

    log("ubuntu user setup for machine router %s [%s / %s] " % (router_name,
                                                                router_ip,
                                                                priv_ip))

    log("router %s %s : %s" % (router_name, router_ip, password))
    __add_ubuntu_user_to_router(router_ip, password, constellation_directory)

    softlayer_scripts_dir = os.path.join(
                    os.path.dirname(launch_utils.softlayer.__file__),
                    'bash')

    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)

    # create a remote cloudsim directory on the router
    ssh_router.cmd("mkdir -p cloudsim")

    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname)
    remote_fname = 'cloudsim/openvpn.key'
    ssh_router.upload_file(openvpn_fname, remote_fname)

    local_fname = os.path.join(softlayer_scripts_dir, 'router_init.bash')
    remote_fname = 'cloudsim/router_init.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    # upload ubuntu user setup scripts
    local_fname = os.path.join(softlayer_scripts_dir, 'auto_ubuntu.bash')
    remote_fname = 'cloudsim/auto_ubuntu.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir, 'create_ubuntu_user.exp')
    remote_fname = 'cloudsim/create_ubuntu_user.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir, 'upload_key.exp')
    remote_fname = 'cloudsim/upload_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir,
                               'process_remote_ssh_key.exp')
    remote_fname = 'cloudsim/process_remote_ssh_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    # avoid ssh error because our server has changed
    constellation.set_value("launch_stage", "init_router")

    create_ssh_key("key-sim", constellation_directory)

    fc1_priv_ip = "0.0.0.0"
    fc2_priv_ip = "0.0.0.0"

    if not partial_deploy:
        fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(
                                osrf_creds, "fc1-%s" % constellation_prefix)
        log("fc1 %s %s" % (fc1_pub_ip, fc1_root_password))
        create_ssh_key("key-fc1", constellation_directory)

        fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(
                                osrf_creds, "fc2-%s" % constellation_prefix)
        log("fc2 %s %s" % (fc2_pub_ip, fc2_root_password))
        create_ssh_key("key-fc2", constellation_directory)

    arg_str = "%s %s %s" % (sim_priv_ip, fc1_priv_ip, fc2_priv_ip)
    cmd = "cd cloudsim; ./router_init.bash /home/ubuntu/cloudsim %s" % arg_str
    # run the script
    constellation.set_value('router_launch_msg', 'generating bash scripts')
    ssh_router.cmd(cmd)

    constellation.set_value('router_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "router", constellation_directory)
    constellation.set_value('sim_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "sim", constellation_directory)
    constellation.set_value('fc1_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "fc1", constellation_directory)
    constellation.set_value('fc2_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "fc2", constellation_directory)


def _provision_ssh_private_machine(constellation_name,
                                   ssh_router,
                                  machine_name_prefix,
                                  private_machine_ip,
                                  machine_password,
                                  startup_script,
                                  constellation_directory):

    constellation = ConstellationState(constellation_name)
    constellation.set_value('%s_launch_msg' % machine_name_prefix,
                                                'User account setup')

    # execute script on router to add ubuntu user on the private machine
    cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-%s.pem.pub" % (
                private_machine_ip, machine_password, machine_name_prefix)
    log(cmd)
    ssh_router.cmd(cmd)

    local_fname = os.path.join(constellation_directory,
                               '%s_startup.bash' % machine_name_prefix)
    with open(local_fname, 'w') as f:
        f.write(startup_script)
    remote_fname = 'cloudsim/%s_startup_script.bash' % machine_name_prefix
    # send startup script to router
    ssh_router.upload_file(local_fname, remote_fname)


def _initialize_private_machines(constellation_name,
                                constellation_prefix,
                                partial_deploy,
                                drcsim_package_name,
                                gpu_driver_list,
                                ppa_list,
                                ros_master_ip,
                                credentials_softlayer,
                                constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= \
                                    launch_sequence.index('init_privates'):
        return
    #
    # router machine
    #
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu',
                           router_ip)

    router_script = get_router_script(ROUTER_IP, SIM_IP, drcsim_package_name)
    local_fname = os.path.join(constellation_directory, 'router_startup.bash')
    with open(local_fname, 'w') as f:
        f.write(router_script)
    remote_fname = 'cloudsim/router_startup_script.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    osrf_creds = load_osrf_creds(credentials_softlayer)
    #
    # sim machine
    #
    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(
                                osrf_creds, "sim-%s" % constellation_prefix)

    sim_script = get_drc_script(drcsim_package_name,
                                SIM_IP,
                                ros_master_ip,
                                gpu_driver_list,
                                ppa_list)

    log("provision sim [%s / %s] %s" % (sim_pub_ip,
                                        sim_priv_ip, sim_root_password))
    _provision_ssh_private_machine(constellation_name,
                                   ssh_router,
                                   "sim",
                                   sim_priv_ip,
                                   sim_root_password,
                                   sim_script,
                                   constellation_directory)
    if not partial_deploy:
        #
        # fc1 machine
        #
        fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(
                                osrf_creds, "fc1-%s" % constellation_prefix)
        fc1_script = get_drc_script(drcsim_package_name,
                                    FC1_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list)

        log("provision fc1 [%s / %s] %s" % (fc1_pub_ip, fc1_priv_ip,
                                            fc1_root_password))
        _provision_ssh_private_machine(constellation_name,
                                       ssh_router,
                                      "fc1",
                                      fc1_priv_ip,
                                      fc1_root_password,
                                      fc1_script,
                                      constellation_directory)
        #
        # fc2 machine
        #
        fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(
                                            osrf_creds,
                                            "fc2-%s" % constellation_prefix)
        fc2_script = get_drc_script(drcsim_package_name,
                                    FC2_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list)

        log("provision fc2 [%s / %s] %s" % (fc2_pub_ip,
                                            fc2_priv_ip,
                                            fc2_root_password))

        _provision_ssh_private_machine(constellation_name,
                                       ssh_router,
                                       "fc2",
                                       fc2_priv_ip,
                                       fc2_root_password,
                                       fc2_script,
                                       constellation_directory)

    log('configure_machines done')
    constellation.set_value("launch_stage", "init_privates")


def _startup_scripts(constellation_name, partial_deploy):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value('constellation_directory')
    # if the change of ip was successful, the script should be in the home
    # directory of each machine
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "change_ip.bash",
                       "packages_setup")

    m = "Executing startup script"
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('router_launch_msg', m)

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    # load packages onto router
    ssh_router.cmd("nohup sudo bash cloudsim/router_startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &")
    # load packages onto simulator
    ssh_router.cmd("cloudsim/sim_init.bash")

    if not partial_deploy:
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)
        # load packages onto fc1
        ssh_router.cmd("cloudsim/fc1_init.bash")
        # load packages onto fc2
        ssh_router.cmd("cloudsim/fc2_init.bash")
        constellation.set_value("fc1_state", "packages_setup")
        constellation.set_value("fc2_state", "packages_setup")

    constellation.set_value("sim_state", "packages_setup")
    constellation.set_value("router_state", "packages_setup")
    constellation.set_value("launch_stage", "startup")


def create_zip_file(zip_file_path, short_name, files_to_zip):

    with zipfile.ZipFile(zip_file_path, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(short_name, short_fname)
            fzip.write(fname, zip_name)


def create_router_zip(router_ip, constellation_name, constellation_directory):
    # create router zip file with keys
    # This file is kept on the server and provides the user with:
    #  - key file for ssh access to the router
    #  - openvpn key
    #  - scripts to connect with ssh, openvpn, ROS setup

    router_machine_dir = os.path.join(constellation_directory, "router")
    os.makedirs(router_machine_dir)

    # copy router-key into router directory
    router_key_short_filename = 'key-router.pem'
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


def __create_private_machine_zip(machine_name_prefix,
                               machine_ip,
                               constellation_name,
                               constellation_directory):

    machine_dir = os.path.join(constellation_directory, machine_name_prefix)
    os.makedirs(machine_dir)
    key_short_filename = 'key-%s.pem' % machine_name_prefix
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


def _create_zip_files(constellation_name,
                     constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('zip'):
        return

    constellation.set_value('router_launch_msg', 'creating zip files')
    router_ip = constellation.get_value("router_public_ip")
    constellation.set_value('router_launch_msg',
                            "creating key zip file bundle")
    router_zip_fname, router_zip_user_fname = create_router_zip(router_ip,
                                                    constellation_name,
                                                    constellation_directory)
    shutil.copy(router_zip_fname, os.path.join(constellation_directory,
                                               "router.zip"))
    shutil.copy(router_zip_user_fname, os.path.join(constellation_directory,
                                                    "user_router.zip"))
    constellation.set_value('router_zip_file', 'ready')
    constellation.set_value('sim_launch_msg', 'creating zip files')

    sim_zip_fname = __create_private_machine_zip("sim", SIM_IP,
                                               constellation_name,
                                               constellation_directory)
    shutil.copy(sim_zip_fname, os.path.join(constellation_directory,
                                            "simulator.zip"))
    constellation.set_value('sim_zip_file', 'ready')

    constellation.set_value('fc1_launch_msg', 'creating zip files')
    fc1_zip_fname = __create_private_machine_zip("fc1", FC1_IP,
                                               constellation_name,
                                               constellation_directory)
    shutil.copy(fc1_zip_fname, os.path.join(constellation_directory,
                                            "field_computer1.zip"))
    shutil.copy(fc1_zip_fname, os.path.join(constellation_directory,
                                            "user_field_computer1.zip"))
    constellation.set_value('fc1_zip_file', 'ready')

    constellation.set_value('fc2_launch_msg', 'creating zip files')
    fc2_zip_fname = __create_private_machine_zip("fc2", FC2_IP,
                                               constellation_name,
                                               constellation_directory)
    shutil.copy(fc2_zip_fname, os.path.join(constellation_directory,
                                            "field_computer2.zip"))
    shutil.copy(fc2_zip_fname, os.path.join(constellation_directory,
                                            "user_field_computer2.zip"))
    constellation.set_value('fc2_zip_file', 'ready')

    constellation.set_value('fc1_launch_msg',
                    'ssh key recovered. Waiting for simulator machine')
    constellation.set_value('fc2_launch_msg',
                    'ssh key recovered. Waiting for simulator machine')

    constellation.set_value("launch_stage", "zip")


def __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       ls_cmd,
                       end_state):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    q = []
    #
    # Wait until machines are online (rebooted?)
    #
    q.append(get_ssh_cmd_generator(ssh_router,
                                        "ls %s" % ls_cmd,
                                        ls_cmd,
                                        constellation,
                                        "router_state",
                                        "running",
                                        max_retries=500))

    q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_sim.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "sim_state",
                                     end_state,
                                     max_retries=500))
    if not partial_deploy:
        q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_fc1.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "fc1_state",
                                     end_state,
                                     max_retries=500))

        q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_fc2.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "fc2_state",
                                     end_state,
                                     max_retries=500))

    empty_ssh_queue(q, sleep=2)


def _reboot_machines(constellation_name,
                    partial_deploy,
                    constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('reboot'):
        return

    m = "Rebooting after software installation"
    s = "rebooting"
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('sim_aws_state', s)

    if not partial_deploy:
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)
        constellation.set_value('fc1_aws_state', s)
        constellation.set_value('fc2_aws_state', s)

    #constellation.set_value('router_aws_state', m)
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "cloudsim/setup/done",
                       "running")

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)

    ssh_router.cmd("cloudsim/reboot_sim.bash")
    if not partial_deploy:
        ssh_router.cmd("cloudsim/reboot_fc1.bash")
        ssh_router.cmd("cloudsim/reboot_fc2.bash")

    constellation.set_value("launch_stage", "reboot")


def _run_machines(constellation_name, partial_deploy, constellation_directory):

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "cloudsim/setup/done",
                       "running")

    constellation = ConstellationState(constellation_name)

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
                constellation.set_value('simulation_glx_state', "not running")
                constellation.set_value('error',
                                        "OpenGL diagnostic failed: %s" % e)
                raise

    #
    # Install gazebo models locally
    # using a utility script from cloudsim-client-tools
    # careful, we are running as root here?
    constellation.set_value('sim_launch_msg', 'Loading Gazebo models')
    ssh_router.cmd("cloudsim/set_vrc_private.bash")
    
    # Final messages
    #
    m = "Complete"
    constellation.set_value('fc1_launch_msg', m)
    constellation.set_value('fc2_launch_msg', m)
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('router_launch_msg', m)

    m = "running"
    constellation.set_value("sim_state", m)
    constellation.set_value("router_state", m)
    constellation.set_value("fc1_state", m)
    constellation.set_value("fc2_state", m)
    constellation.set_value("constellation_state", m)

    m = "running"
    constellation.set_value('fc1_aws_state', m)
    constellation.set_value('fc2_aws_state', m)
    constellation.set_value('sim_aws_state', m)
    constellation.set_value('router_aws_state', m)

    constellation.set_value("launch_stage", "running")


def _change_ip_addresses(constellation_name,
                        partial_deploy,
                        credentials_softlayer,
                        constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'change_ip'):
        return
    m = "Setting private IP address"
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('router_launch_msg', m)

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    # change ip on sim
    ssh_router.cmd("cloudsim/set_sim_ip.bash")
    # change ip on router
    ssh_router.cmd("nohup sudo bash change_ip.bash %s > ssh_change_ip.out 2> ssh_change_ip.err < /dev/null &" % ROUTER_IP)

    if not partial_deploy:
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)
        ssh_router.cmd("cloudsim/set_fc1_ip.bash")
        ssh_router.cmd("cloudsim/set_fc2_ip.bash")

    constellation.set_value("launch_stage", "change_ip")


def _shutdown_constellation_public_ips(constellation_name,
                                      constellation_prefix,
                                      partial_deploy,
                                      credentials_softlayer,
                                      constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                    "block_public_ips"):
        return

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "cloudsim/setup/done",
                       "running")

    m = "Switching off public network interfaces"
    constellation.set_value('sim_launch_msg', m)
    #constellation.set_value('router_launch_msg', m)
    private_machines = ["sim-%s" % constellation_prefix]
    if not partial_deploy:
        private_machines.append("fc1-%s" % constellation_prefix)
        private_machines.append("fc2-%s" % constellation_prefix)
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)

    osrf_creds = load_osrf_creds(credentials_softlayer)
    shutdown_public_ips(osrf_creds, private_machines)
    constellation.set_value("launch_stage", "block_public_ips")


def launch(username, config, constellation_name, tags,
           constellation_directory):
    """
    Called by cloudsimd when it receives a launch message
    """

    log("launch constellation name: %s" % constellation_name)

    drc_package = "drcsim"
    ppa_list = []  # ['ubuntu-x-swat/x-updates']
    gpu_driver_list = ['nvidia-current',
                       'nvidia-settings',
                       'nvidia-current-dev']
    # if true, the machines are reloaded. This is done in the case
    # of partial reload because the terminate button would wipe out 
    # all machines

    partial_deploy = False
    if config.find("partial") > 0:
        partial_deploy = True
    log("partial deploy: %s (only sim and router)" % partial_deploy)

    if config.find("nightly") >= 0:
        drc_package = "drcsim-nightly"
    elif config.find("nvidia 319") >= 0:
        ppa_list = ['xorg-edgers/ppa']
        gpu_driver_list = ["nvidia-319", 'nvidia-settings']

    constellation_prefix = config.split()[-1]

    log("constellation_prefix %s" % constellation_prefix)
    log("DRC package %s" % drc_package)
    log("ppas: %s" % ppa_list)
    log("gpu packages %s" % gpu_driver_list)

    cs_cfg = get_cloudsim_config()
    credentials_softlayer = cs_cfg['softlayer_path']
    log("softlayer %s" % credentials_softlayer)
    constellation = ConstellationState(constellation_name)

    constellation.set_value("launch_stage", "os_reload")

    _init_computer_data(constellation_name)
#         _reload_os_machines(constellation_name,
#                            constellation_prefix,
#                            partial_deploy,
#                            credentials_softlayer)
    _wait_for_constellation_reload(constellation_name,
                                constellation_prefix,
                                partial_deploy,
                                credentials_softlayer)

    log("Initialize router: %s" % constellation_name)
    # set ubuntu user and basic scripts on router
    _initialize_router(constellation_name,
                      constellation_prefix,
                      partial_deploy,
                      credentials_softlayer,
                      constellation_directory)

    # set ubuntu user and basic scripts on fc1, fc2 and sim
    ros_master_ip = SIM_IP

    _initialize_private_machines(constellation_name,
                                constellation_prefix,
                                partial_deploy,
                                drc_package,
                                gpu_driver_list,
                                ppa_list,
                                ros_master_ip,
                                credentials_softlayer,
                                constellation_directory)

    # router, sim, fc1 and fc2 zip files
    _create_zip_files(constellation_name,
                      constellation_directory)
    # edit /etc/network/interfaces and restart networking on all machines
    _change_ip_addresses(constellation_name,
                        partial_deploy,
                        credentials_softlayer,
                        constellation_directory)
    # launch startup scripts
    _startup_scripts(constellation_name, partial_deploy)
    # disable access to sim fc1 and fc2 via their public ip addresses
    _shutdown_constellation_public_ips(constellation_name,
                                      constellation_prefix,
                                      partial_deploy,
                                      credentials_softlayer,
                                      constellation_directory)

    # reboot fc1, fc2 and sim (but not router)
    _reboot_machines(constellation_name,
                    partial_deploy,
                    constellation_directory)
    # wait for machines to be back on line
    _run_machines(constellation_name, partial_deploy, constellation_directory)


def terminate(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_prefix = constellation_name.split('_')[-1]

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
    credentials_softlayer = cs_cfg['softlayer_path']
    log("softlayer %s" % credentials_softlayer)
    constellation.set_value("launch_stage", "nothing")
    
    partial = False
    _reload_os_machines(constellation_name,
                       constellation_prefix,
                       partial,
                       credentials_softlayer)
    
#     for prefix in ['router','sim','fc1','fc2']:
#         constellation.set_value('%s_aws_state' % prefix, 'pending')
#     
#     machines_dict = {'sim-%s' % constellation_prefix: 'sim_launch_msg',
#                      'router-%s' % constellation_prefix: 'router_launch_msg',
#                      'fc2-%s' % constellation_prefix: 'fc2_launch_msg',
#                      'fc1-%s' % constellation_prefix: 'fc1_launch_msg',
#                     }
#     reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
#     osrf_creds = load_osrf_creds(credentials_softlayer)
#     wait_for_server_reloads(osrf_creds, machines_dict.keys(), reload_monitor.callback)
    
    constellation.set_value('sim_state', 'terminated')
    constellation.set_value('sim_launch_msg', "terminated")
    constellation.set_value('router_state', 'terminated')
    constellation.set_value('router_launch_msg', "terminated")
    constellation.set_value('field1_state', 'terminated')
    constellation.set_value('field1_launch_msg', "terminated")
    constellation.set_value('field2_state', 'terminated')
    constellation.set_value('field2_launch_msg', "terminated")
    constellation.set_value('constellation_state', 'terminated')


class MonitorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxb49a97c4'
        cred = get_softlayer_path()

        monitor(user, const, cred)


class VrcCase(unittest.TestCase):

    def atest_startup(self):
        constellation_name = 'test_vrc_contest_toto'
        _startup_scripts(constellation_name)

    def atest_zip_create(self):
        constellation_name = "toto"
        constellation_directory = os.path.join(get_test_path("zip_test"))
        router_ip = '50.23.225.173'
        create_router_zip(router_ip, constellation_name, constellation_directory)
        __create_private_machine_zip("fc1", FC1_IP, constellation_name, constellation_directory)

#     def test_script(self):
#         s = get_sim_script('drcsim')
#         print(s)
#         print("")

    def atest_launch(self):

        constellation_prefix = "02"
        launch_stage = None  # use the current stage

        launch_stage = "nothing"
        launch_stage = "os_reload"
        #"nothing", "os_reload", "init_router", "init_privates", "zip",  "change_ip", "startup", "reboot", "running"
        launch_stage = "running"

        self.constellation_name = 'test_vrc_contest_%s' % constellation_prefix
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer = get_softlayer_path()
        CONFIGURATION = 'vrc_contest'
        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name = get_unique_short_name(test_name + "_")
            self.constellation_directory = os.path.abspath(os.path.join(get_test_path(test_name), self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            self.constellation_directory = os.path.abspath(os.path.join(get_test_path(test_name), self.constellation_name))

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory", self.constellation_directory)
        constellation.set_value("configuration", 'vrc_contest')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        self.tags = {'TestCase': CONFIGURATION, 'configuration': CONFIGURATION, 'constellation': self.constellation_name, 'user': self.username, 'GMT': "now"}

        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)
        config = "OSRF VRC Constellation %s" % constellation_prefix

        launch(self.username, config, self.constellation_name, self.tags, self.constellation_directory)

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

    def Xtest_router_ubuntu(self):
        directory = get_test_path('test_router_ubuntu')
        router_ip = '50.97.149.39'
        password = 'SapRekx3'
        os.makedirs(directory)
        print("__add_ubuntu_user_to_router %s %s %s" % (router_ip, password, directory))
        __add_ubuntu_user_to_router(router_ip, password, directory)
        s = "ssh -i %s/key-router.pem ubuntu@%s" % (directory, router_ip)
        print(s)

    def stest_ubuntu_user_on_sim_from_router(self):

        constellation = ConstellationState('test_vrc_contest_toto')

        constellation_directory = constellation.get_value("constellation_directory")
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
        credentials_softlayer = get_softlayer_path()
        osrf_creds = load_osrf_creds(credentials_softlayer)

        pub_ip, ip, password = get_machine_login_info(osrf_creds, "sim-01")
        log("setting up ubuntu user on simulator machine [%s / %s]" % (pub_ip, ip))
        cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-sim.pem.pub" % (ip, password)
        log(cmd)
        out = ssh_router.cmd(cmd)
        log(out)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate()
        # self.constellation_name =
        #terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
