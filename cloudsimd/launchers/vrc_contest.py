from __future__ import print_function

import unittest
import os
import time
import zipfile


from shutil import copyfile


import redis
import logging

from launch_utils.traffic_shapping import  run_tc_command

import launch_utils.softlayer

from launch_utils.monitoring import constellation_is_terminated,\
    monitor_launch_state, monitor_simulator, monitor_cloudsim_ping,\
    get_ssh_client
import shutil
from launch_utils.softlayer import load_osrf_creds, reload_servers,\
    get_softlayer_path, wait_for_server_reloads, get_machine_login_info,\
    setup_ssh_key_access, create_ssh_key, create_openvpn_key
from launch_utils.launch_db import get_constellation_data, ConstellationState
from launch_utils import sshclient
from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.launch import get_unique_short_name
from launch_utils.startup_scripts import create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file,\
    create_ssh_connect_file
from launch_utils.sshclient import SshClient, clean_local_ssh_key_entry
from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue




ROUTER_IP='10.0.0.50'
SIM_IP='10.0.0.51'
FC1_IP='10.0.0.52'
FC2_IP='10.0.0.53'
OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'
    
def log(msg, channel = "vrc_contest"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("vrc_contest log> %s" % msg)


def get_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)



def start_simulator(constellation, package_name, launch_file_name, launch_args, task_timeout):

     
    constellation_dict = get_constellation_data(  constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_name    = constellation_dict['sim_key_name']
 
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    c = "bash cloudsim/start_sim.bash %s %s %s" %(package_name, launch_file_name, launch_args)
    cmd = c.strip()
    ssh_sim = sshclient(sim_machine_dir, sim_key_name, 'ubuntu', sim_ip)
 
    r = ssh_sim.cmd(cmd)
    log('start_simulator %s' % r)


def stop_simulator(constellation):
    constellation_dict = get_constellation_data( constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_name    = constellation_dict['sim_key_name']
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_sim = SshClient(sim_machine_dir, sim_key_name, 'ubuntu', sim_ip)
    r = ssh_sim.cmd(cmd)
    log('stop_simulator %s' % r)


def start_task(constellation, task):
    
    log("** SIMULATOR *** start_task %s" % task)

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation, 'sim_machine_name', 'sim_key_name', 'simulation_ip', latency, up, down)
    
    log("** START SIMULATOR ***")
    start_simulator(constellation, task['ros_package'], task['ros_launch'], task['ros_args'], task['timeout'])
    
    

        
    
def stop_task(constellation):
    
    log("** SIMULATOR *** STOP TASK %s ***" % constellation)

    latency = 0 
    up = -1
    down = -1
    log("** TC COMMAND ***")
    run_tc_command(constellation, 'sim_machine_name', 'sim_key_name', 'simulation_ip', latency, up, down)
    
    log("** stop simulator ***")
    stop_simulator(constellation)
    

def monitor(username, constellation_name, credentials_ec2, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True
    
    constellation = ConstellationState( constellation_name)
   
    simulation_state = constellation.get_value('sim_state')
    sim_ssh = get_ssh_client(constellation_name, simulation_state,'sim_ip_address', 'sim_key_name' )
    monitor_cloudsim_ping(constellation_name, 'sim_ip_address', 'sim_latency')
    monitor_launch_state(constellation_name, sim_ssh, simulation_state, "tail -1 /var/log/dpkg.log ", 'sim_launch_msg')
    
    monitor_simulator(constellation_name, sim_ssh)
    
    router_state = constellation.get_value('router_state')
    ssh_router = get_ssh_client(constellation_name, router_state,'router_ip_address', 'router_key_name' )
    monitor_cloudsim_ping(constellation_name, 'router_ip_address', 'router_latency')
    monitor_launch_state(constellation_name, ssh_router, router_state, "tail -1 /var/log/dpkg.log", 'router_launch_msg')
    
    field1_state = constellation.get_value('field1_state')
    ssh_field1 = get_ssh_client(constellation_name, field1_state,'field1_ip_address', 'field1_key_name' )
    monitor_cloudsim_ping(constellation_name, 'field1_ip_address', 'field1_latency')
    monitor_launch_state(constellation_name, ssh_field1, field1_state, "tail -1 /var/log/dpkg.log", 'field1_launch_msg')
    
    field2_state = constellation.get_value('field2_state')
    ssh_field2 = get_ssh_client(constellation_name, field2_state,'field2_ip_address', 'field1_key_name' )
    monitor_cloudsim_ping(constellation_name, 'field2_ip_address', 'field2_latency')
    monitor_launch_state(constellation_name, ssh_field2, field2_state, "tail -1 /var/log/dpkg.log", 'field2_launch_msg')
    # log("monitor not done")
    return False





def init_computer_data(constellation_name, prefixes):
    constellation = ConstellationState( constellation_name)
    for prefix in prefixes:
        constellation.set_value('%s_ip_address' % prefix, "nothing")
        constellation.set_value('%s_state' % prefix, "nothing")
        constellation.set_value('%s_aws_state'% prefix, 'nothing')
        constellation.set_value('%s_launch_msg'% prefix, 'starting')
        constellation.set_value('%s_zip_file'% prefix, 'not ready')
        constellation.set_value('%s_latency'% prefix, '[]')
        constellation.set_value('%s_aws_reservation_id'% prefix, 'nothing')
        constellation.set_value('%s_machine_name' % prefix, '%s_%s' % (prefix, constellation_name) )
        constellation.set_value('%s_key_name'% prefix, None)



def get_router_script(machine_ip, ros_master_ip):

    
    s= """#!/bin/bash
# Exit on error
set -ex
exec >/home/ubuntu/launch_stdout_stderr.log 2>&1


# Add OSRF repositories
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -

# ROS setup
sh -c 'echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list'
wget http://packages.ros.org/ros.key -O - | sudo apt-key add -

apt-get update

apt-get install -y ntp
apt-get install -y openvpn

cat <<DELIM > /etc/openvpn/openvpn.conf
dev tun
ifconfig """ + OPENVPN_SERVER_IP + " " + OPENVPN_CLIENT_IP + """
secret static.key
DELIM



#
# The openvpn key is generated in CloudSim

#
cp /home/ubuntu/cloudsim/openvpn.key /etc/openvpn/static.key
chmod 644 /etc/openvpn/static.key

service openvpn restart

sysctl -w net.ipv4.ip_forward=1
iptables -A FORWARD -i tun0 -o bond0 -j ACCEPT
iptables -A FORWARD -o tun0 -i bond0 -j ACCEPT

# That could be removed if ros-comm becomes a dependency of cloudsim-client-tools
sudo apt-get install -y ros-fuerte-ros-comm

# roscore is in simulator's machine
cat <<DELIM >> /etc/environment
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311
export ROS_IP=""" + machine_ip + """
source /opt/ros/fuerte/setup.sh
DELIM

apt-get install -y cloudsim-client-tools

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

# Create upstart vrc_controller job
cat <<DELIM > /etc/init/vrc_controller.conf
# /etc/init/vrc_controller.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -s 0.5 -v -d eth0 > /var/log/vrc_controller.log 2>&1

respawn
DELIM

# Create upstart vrc_bandwidth job
cat <<DELIM > /etc/init/vrc_bandwidth.conf
# /etc/init/vrc_bandwidth.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero<caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_wrapper.sh vrc_bandwidth.py -d /tmp > /var/log/vrc_bandwidth.log 2>&1

respawn
DELIM

# start vrc_sniffer and vrc_controllers
start vrc_sniffer
start vrc_controller
start vrc_bandwidth

mkdir -p /home/ubuntu/cloudsim/setup
touch /home/ubuntu/cloudsim/setup/done
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

"""
    return s

def get_fc2_script(drc_package_name, machine_ip = FC2_IP):
    s = get_drc_script(drc_package_name, machine_ip)
    return s

def get_fc1_script(drc_package_name, machine_ip = FC1_IP):
    s = get_drc_script(drc_package_name, machine_ip)
    return s

def get_sim_script(drc_package_name, machine_ip = SIM_IP):
    s = get_drc_script(drc_package_name, machine_ip)
    return s

    
def get_drc_script(drc_package_name, machine_ip):
    
    drc_package_name = "drcsim"
    pcibus_id = "130"
    ros_master_ip = SIM_IP
    
    s = """#!/bin/bash
# Exit on error
set -ex
# Redirect everybody's output to a file
logfile=/home/ubuntu/launch_stdout_stderr.log
exec > $logfile 2>&1


#cat <<DELIM >> /etc/apt/sources.list
#deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise multiverse
#DELIM

mkdir /home/ubuntu/cloudsim
mkdir /home/ubuntu/cloudsim/setup

 
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

insmod /lib/modules/`uname -r`/kernel/drivers/net/ethernet/intel/ixgbe/ixgbe.ko

exit 0
DELIM


cat <<DELIM > /home/ubuntu/cloudsim/start_sim.bash

echo \`date\` "\$1 \$2 \$3" >> /home/ubuntu/cloudsim/start_sim.log

. /usr/share/drcsim/setup.sh 
export ROS_IP=""" + machine_ip +""" 
export GAZEBO_IP=""" + machine_ip +"""
export DISPLAY=:0 
roslaunch \$1 \$2 \$3 gzname:=gzserver  &

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/stop_sim.bash

killall -INT roslaunch

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/ros.bash

# To connect via ROS:

# ROS's setup.sh will overwrite ROS_PACKAGE_PATH, so we'll first save the existing path
oldrpp=$ROS_PACKAGE_PATH

. /usr/share/drcsim/setup.sh
eval export ROS_PACKAGE_PATH=\$oldrpp:\\$ROS_PACKAGE_PATH
export ROS_IP=""" + machine_ip +"""
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311 

export GAZEBO_IP=""" + machine_ip +"""
export GAZEBO_MASTER_URI=http://""" + ros_master_ip + """:11345

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/ping_gl.bash

DISPLAY=localhost:0 timeout 10 glxinfo

DELIM


chown -R ubuntu:ubuntu /home/ubuntu/cloudsim  

# Add ROS and OSRF repositories
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

date >> /home/ubuntu/setup.log
echo 'setting up the ros and drc repos keys' >> /home/ubuntu/setup.log
wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -
    
echo "update packages" >> /home/ubuntu/setup.log
apt-get update || apt-get update || apt-get update

 
cat <<DELIM > /etc/init.d/vpcroute
#! /bin/sh

case "\$1" in
  start|"")
        route add """ + OPENVPN_CLIENT_IP+""" gw """ + ROUTER_IP+"""
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
ln -s /etc/init.d/vpcroute /etc/rc2.d/S99vpcroute

# invoke it now to add route to the router
/etc/init.d/vpcroute start 
    
echo "install X, with nvidia drivers" >> /home/ubuntu/setup.log
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` nvidia-current nvidia-current-dev gnome-session-fallback
    
#
# The BusID is given by lspci (but lspci gives it in hex, and BusID needs dec)
# This value is required for Tesla cards
cat <<DELIM > /etc/X11/xorg.conf

# take the hex from lspci and turn it into dec
# root@gpu02:/home/ubuntu# lspci | grep Tesla

# SOFTLAYER
# 82:00.0 3D controller: NVIDIA Corporation Tesla M2090 (rev a1)
# 82 hex is 130 dec
# Amazon is 3 dec for cg1.4xLarge

Section "ServerLayout"
    Identifier     "Layout0"
    Screen      0  "Screen0"
EndSection
Section "Monitor"
    Identifier     "Monitor0"
    VendorName     "Unknown"
    ModelName      "Unknown"
    HorizSync       28.0 - 33.0
    VertRefresh     43.0 - 72.0
    Option         "DPMS"
EndSection
Section "Device"
    Identifier     "Device0"
    Driver         "nvidia"
    BusID          "PCI:0:""" + pcibus_id + """:0"
    VendorName     "NVIDIA Corporation"
EndSection
Section "Screen"
    Identifier     "Screen0"
    Device         "Device0"
    Monitor        "Monitor0"
    DefaultDepth    24
    SubSection     "Display"
        Depth       24
    EndSubSection
EndSection
DELIM


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

apt-get install -y ntp 

echo "install """ + drc_package_name+ """ ">> /home/ubuntu/setup.log
apt-get install -y """ + drc_package_name+ """

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

# Create upstart vrc_controller job
cat <<DELIM > /etc/init/vrc_controller.conf
# /etc/init/vrc_controller.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -v -d eth0 > /var/log/vrc_controller.log 2>&1

respawn
DELIM

# start vrc_sniffer and vrc_controllers
start vrc_sniffer
start vrc_controller

 
 
touch /home/ubuntu/cloudsim/setup/done

"""
    return s
    




    
    
launch_sequence = ["nothing", "os_reload", "init_router", "init_privates", "configure", "startup", "reboot", "running"]    

class ReloadOsCallBack(object):
    def __init__(self, constellation_name, machines_dict):
        self.constellation_name = constellation_name
        self.machines_dict = machines_dict
        self.constellation_state = ConstellationState(constellation_name)
    
    def callback(self, machine_name, state):
        msg_key = self.machines_dict[machine_name]
        log( "[%s] %s [%s] %s" % (self.constellation_name, machine_name, msg_key, state))
        self.constellation_state.set_value(msg_key, state)
    
    
def reload_os_machines(constellation_name, constellation_prefix, osrf_creds_fname):

    constellation = ConstellationState( constellation_name)
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('os_reload'):
        return
    
    constellation.set_value("constellation_state", "launching")
    constellation.set_value("error", "")
    
    constellation.set_value("configuration_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")
    
    constellation.set_value("fc1_ip", "xxx")
    constellation.set_value("fc2_ip", "xxx")
    constellation.set_value("sim_ip", "xxx")

    constellation.set_value('fc1_launch_msg', 'nothing')
    constellation.set_value('fc2_launch_msg', 'nothing')
    constellation.set_value('simulation_launch_msg', 'nothing')


    constellation.set_value("fc1_aws_id", "xxx")
    constellation.set_value("fc2_aws_id", "xxx")
    constellation.set_value("simulation_aws_id", "xxx")
    constellation.set_value("router_aws_id", "xxx")
    
    machine_names_prefix = ('router','sim' , 'fc2', 'fc1')
    init_computer_data(constellation_name, machine_names_prefix)

    constellation.set_value("error", "")
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    

    # compute the softlayer machine names
    machine_names = [x + "-" + constellation_prefix for x in  machine_names_prefix]
    reload_servers(osrf_creds, machine_names)
    
    constellation.set_value("launch_stage", "os_reload")    
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")


def add_ubuntu_user_to_router(router_ip, password, constellation_directory):
    
    clean_local_ssh_key_entry(router_ip)
    create_ssh_key('key-router', constellation_directory)
    # setup a ubuntu sudoer no password user with an ssh key
    router_pub_key_path = os.path.join(constellation_directory, "key-router.pem.pub"  )
    setup_ssh_key_access(router_ip, password, router_pub_key_path)
    router_priv_key_path = os.path.join(constellation_directory, "key-router.pem"  )
    log ("ssh -i %s ubuntu@%s" % (router_priv_key_path, router_ip))    


def upload_ssh_keys_to_router(ssh_router, machine_prefix, constellation_directory):
    # upload public key to router
    local_fname = os.path.join(constellation_directory, 'key-%s.pem.pub' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem.pub' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload public key %s to %s" % (local_fname, remote_fname))

    # upload private key to router
    local_fname = os.path.join(constellation_directory, 'key-%s.pem' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload private key %s to %s" % (local_fname, remote_fname))
    
def upload_user_scripts_to_router(router_ip, constellation_directory, sim_ip, fc1_ip, fc2_ip):

    softlayer_scripts_dir = os.path.join( os.path.dirname(launch_utils.softlayer.__file__), 'bash')
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    # create a remote cloudsim directory on the router
    ssh_router.cmd("mkdir -p cloudsim")
    
    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname) 
    remote_fname = 'cloudsim/openvpn.key'
    ssh_router.upload_file(openvpn_fname, remote_fname)
    
    # upload keys (useful when switching computers)
    upload_ssh_keys_to_router(ssh_router, "router", constellation_directory)
    
    local_fname = os.path.join( softlayer_scripts_dir, 'router_init.bash')
    remote_fname = 'cloudsim/router_init.bash'
    ssh_router.upload_file(local_fname,remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    # run the script
    ssh_router.cmd("cd cloudsim; ./router_init.bash /home/ubuntu/cloudsim %s %s %s" % (sim_ip, fc1_ip, fc2_ip))

    # upload ubuntu user setup scripts
    local_fname = os.path.join( softlayer_scripts_dir, 'auto_ubuntu.bash')
    remote_fname = 'cloudsim/auto_ubuntu.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join( softlayer_scripts_dir, 'create_ubuntu_user.exp')
    remote_fname = 'cloudsim/create_ubuntu_user.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join( softlayer_scripts_dir, 'upload_key.exp')
    remote_fname = 'cloudsim/upload_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join( softlayer_scripts_dir, 'process_remote_ssh_key.exp')
    remote_fname = 'cloudsim/process_remote_ssh_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))



    
    

def initialize_router(constellation_name, constellation_prefix, osrf_creds_fname, constellation_directory):
    
    constellation = ConstellationState( constellation_name)
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init_router'):
        return
    
    if os.path.exists(constellation_directory):
        shutil.rmtree(constellation_directory)
    os.makedirs(constellation_directory)

    machines_dict = {'sim-%s' % constellation_prefix:'simulation_launch_msg',
                     'router-%s' % constellation_prefix:'router_launch_msg', 
                     'fc2-%s' % constellation_prefix:'fc2_launch_msg', 
                     'fc1-%s' % constellation_prefix:'fc1_launch_msg',
                    }
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)    
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
    wait_for_server_reloads(osrf_creds, machines_dict.keys(), reload_monitor.callback)

    router_name = "router-%s" % constellation_prefix
    
    router_ip, priv_ip, password = get_machine_login_info(osrf_creds, router_name) 
    constellation.set_value("router_public_ip", router_ip )
    
    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(osrf_creds, "sim-%s" % constellation_prefix)
    fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(osrf_creds, "fc1-%s" % constellation_prefix)
    fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(osrf_creds, "fc2-%s" % constellation_prefix)
    
    
    log("ubuntu user setup for machine router %s [%s / %s] " % (router_name, router_ip, priv_ip) )
    # dst_dir = os.path.abspath('.')
    
    log("router %s %s : %s" % (router_name, router_ip, password))
    add_ubuntu_user_to_router(router_ip, password, constellation_directory)

    upload_user_scripts_to_router(router_ip, constellation_directory, sim_priv_ip, fc1_priv_ip, fc2_priv_ip)
    # avoid ssh error because our server has changed
    constellation.set_value("launch_stage", "init_router")


    
def initialize_private_machines(constellation_name, constellation_prefix, drcsim_package_name, credentials_softlayer, constellation_directory):
    
    
    def provision_ssh_private_machine(ssh_router, machine_name_prefix, private_machine_ip, machine_password, startup_script, constellation_directory ):
        
        create_ssh_key("key-%s" % machine_name_prefix, constellation_directory)
        upload_ssh_keys_to_router(ssh_router,  machine_name_prefix, constellation_directory)
    
        # execute script on router to add ubuntu user on the private machine
        cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-%s.pem.pub" % (private_machine_ip, machine_password, machine_name_prefix)
        log(cmd)
        ssh_router.cmd(cmd)
    
        local_fname = os.path.join(constellation_directory, '%s_startup.bash' % machine_name_prefix)
        with open(local_fname, 'w') as f:
            f.write(startup_script)
        remote_fname = 'cloudsim/%s_startup_script.bash' % machine_name_prefix
        # send startup script to router
        ssh_router.upload_file(local_fname, remote_fname)
        
        
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init_privates'):
        return

    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)

    router_script = get_router_script(ROUTER_IP, SIM_IP)
    local_fname = os.path.join(constellation_directory, 'router_startup.bash')
    with open(local_fname, 'w') as f:
        f.write(router_script)
    remote_fname = 'cloudsim/router_startup_script.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
            
    osrf_creds = load_osrf_creds(credentials_softlayer)

    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(osrf_creds, "sim-%s" % constellation_prefix)
    sim_script = get_sim_script(drcsim_package_name)
    log("provision sim [%s / %s] %s" % (sim_pub_ip, sim_priv_ip, sim_root_password))
    provision_ssh_private_machine(ssh_router, "sim",  sim_priv_ip, sim_root_password, sim_script, constellation_directory)

    fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(osrf_creds, "fc1-%s" % constellation_prefix)
    fc1_script = get_fc1_script(drcsim_package_name)
    log("provision fc1 [%s / %s] %s" % (fc1_pub_ip, fc1_priv_ip, fc1_root_password))
    provision_ssh_private_machine(ssh_router, "fc1", fc1_priv_ip, fc1_root_password, fc1_script, constellation_directory)

    fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(osrf_creds, "fc2-%s" % constellation_prefix)
    fc2_script = get_fc2_script(drcsim_package_name)
    log("provision fc2 [%s / %s] %s" % (fc2_pub_ip, fc2_priv_ip, fc2_root_password))
    provision_ssh_private_machine(ssh_router, "fc2", fc2_priv_ip, fc2_root_password, fc2_script, constellation_directory)

    log('configure_machines done')    
    constellation.set_value("launch_stage", "init_privates")

def startup_scripts(constellation_name):
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value('constellation_directory')

    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)    
    
    # load packages onto router
    ssh_router.cmd("nohup sudo bash cloudsim/router_startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &")
    # load packages onto fc1
    ssh_router.cmd("cloudsim/fc1_init.bash")
    # load packages onto fc2
    ssh_router.cmd("cloudsim/fc2_init.bash")
    # load packages onto simulator
    ssh_router.cmd("cloudsim/sim_init.bash")

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
    os.makedirs(router_machine_dir )
    
    # copy router-key into router directory
    router_key_short_filename = 'key-router.pem'
    router_key_path =  os.path.join(router_machine_dir, router_key_short_filename)
    copyfile(os.path.join(constellation_directory, router_key_short_filename), router_key_path)
    os.chmod(router_key_path, 0600)
    
    vpn_key_short_filename = 'openvpn.key'
    vpnkey_fname =  os.path.join(router_machine_dir, vpn_key_short_filename)
    copyfile(os.path.join(constellation_directory, vpn_key_short_filename), vpnkey_fname)
    os.chmod(vpnkey_fname, 0600)
    
    # create open vpn config file
    file_content = create_openvpn_client_cfg_file(router_ip, client_ip = OPENVPN_CLIENT_IP, server_ip = OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(router_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    
    fname_start_vpn = os.path.join(router_machine_dir , "start_vpn.bash")    
    file_content = create_vpc_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755)
    
    fname_ros = os.path.join(router_machine_dir, "ros.bash")    
    file_content = create_ros_connect_file(machine_ip=OPENVPN_CLIENT_IP, master_ip=SIM_IP)
    
    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    
    fname_ssh_sh =  os.path.join(router_machine_dir,'ssh-router.bash')
    file_content = create_ssh_connect_file(router_key_short_filename, router_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)
    
    # wait (if necessary) for openvpn key to have been generated

    #creating zip
    files_to_zip = [ router_key_path, 
                     fname_start_vpn,
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    router_fname_zip = os.path.join(router_machine_dir, "router_%s.zip" % constellation_name)
    create_zip_file(router_fname_zip, "router_%s" % constellation_name, files_to_zip)


def create_private_machine_zip(machine_name_prefix, machine_ip, constellation_name, constellation_directory):
    
    machine_dir = os.path.join(constellation_directory, machine_name_prefix)
    os.makedirs(machine_dir )
    key_short_filename = 'key-%s.pem' % machine_name_prefix
    key_fpath =  os.path.join(machine_dir, key_short_filename)
    copyfile(os.path.join(constellation_directory,   key_short_filename), key_fpath)
    os.chmod(key_fpath, 0600)
    
    fname_ssh_sh =  os.path.join(machine_dir,'ssh-%s.bash' % machine_name_prefix)
    file_content = create_ssh_connect_file(key_short_filename, machine_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)    
    
    files_to_zip = [ key_fpath, 
                     fname_ssh_sh,]
    
    fname_zip = os.path.join(machine_dir, "%s_%s.zip" % (machine_name_prefix, constellation_name) )
    create_zip_file(fname_zip, "%s_%s" % (machine_name_prefix, constellation_name), files_to_zip)

    
    
def configure_ssh(constellation_name, constellation_directory):

    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('configure'):
        return

    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)

    constellation.set_value('router_launch_msg',   "creating key zip file bundle")

    create_router_zip(router_ip, constellation_name, constellation_directory)
    constellation.set_value('router_zip_file', 'ready')#
 
    # ZIP files
    # First, create 3 directories (using machine names) and copy pem key files there 
    
    create_private_machine_zip("fc1", FC1_IP, constellation_name, constellation_directory)
    constellation.set_value('fc1_zip_file', 'ready')
    
    create_private_machine_zip("fc2", FC2_IP, constellation_name, constellation_directory)   
    constellation.set_value('fc2_zip_file', 'ready')

    create_private_machine_zip("sim", SIM_IP, constellation_name, constellation_directory)
    constellation.set_value('sim_zip_file', 'ready')
    


    constellation.set_value("launch_stage", "configure")    



def wait_for_setup_done(constellation_name, constellation_directory):
    constellation = ConstellationState( constellation_name)   
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return
    
    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    #
    # Wait until machines are online (rebooted?)
    #
    router_done = get_ssh_cmd_generator(ssh_router,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "router_state", "running",  max_retries = 500)
    sim_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "sim_state", "running",  max_retries = 500)
    fc1_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_fc1.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "fc1_state", "running",  max_retries = 500)
    fc2_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_fc2.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "fc2_state", "running",  max_retries = 500)
    empty_ssh_queue([router_done, sim_done, fc1_done, fc2_done], sleep=2)
  

def reboot_machines(constellation_name, constellation_directory):
    
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'reboot':
        return
    
    wait_for_setup_done(constellation_name, constellation_directory)
        
    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    ssh_router.cmd("cloudsim/reboot_sim.bash")
    ssh_router.cmd("cloudsim/reboot_fc1.bash")
    ssh_router.cmd("cloudsim/reboot_fc2.bash")
           
    constellation.set_value("launch_stage", "reboot")

def run_machines(constellation_name, constellation_directory): 
    wait_for_setup_done(constellation_name, constellation_directory)
    
    constellation = ConstellationState( constellation_name)
    constellation.set_value("launch_stage", "running")

def change_ip_addresses(constellation_directory):
    
    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    change_ip = """# change ip
set -ex
exec > ./change_ip_$2_to_$3.log 2>&1

file=$1
new_ip=$2

cp $file interfaces.back
rm $file
sed  "s/^address 10.41.*/address $new_ip/" interfaces.back > interfaces.new
cp interfaces.new $file

/etc/init.d/networking restart
echo done
    """
    ssh_router.create_file(change_ip, "cloudsim/change_ip.bash")
    

def launch(username, constellation_name, constellation_prefix, credentials_softlayer, constellation_directory ):

    drc_package = "drcsim"
    constellation = ConstellationState( constellation_name)
    if not constellation.has_value("launch_stage"):
        constellation.set_value("launch_stage", "nothing")
   
    reload_os_machines(constellation_name, constellation_prefix, credentials_softlayer)
    change_ip_addresses(constellation_directory)
    initialize_router(constellation_name, constellation_prefix, credentials_softlayer, constellation_directory)
    initialize_private_machines(constellation_name, constellation_prefix, drc_package, credentials_softlayer, constellation_directory)

    configure_ssh(constellation_name, constellation_directory)
    startup_scripts(constellation_name)
    reboot_machines(constellation_name, constellation_directory)
    run_machines(constellation_name, constellation_directory)

def terminate(constellation_name, osrf_creds_fname):

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    constellation = ConstellationState( constellation_name)
    
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
        
#  wait_for_multiple_machines_to_terminate(ec2conn, 

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
        
        monitor(user, const, cred, 1)
        
  
class VrcCase(unittest.TestCase):
    
    def atest_startup(self):
        constellation_name = 'test_vrc_contest_toto'
        startup_scripts(constellation_name)
    
    def atest_zip_create(self):
        constellation_name = "toto"
        constellation_directory =  os.path.join(get_test_path("zip_test"))
        router_ip = '50.23.225.173'
        
        
        
        create_router_zip(router_ip, constellation_name, constellation_directory)
        create_private_machine_zip("fc1", FC1_IP, constellation_name, constellation_directory)
    
    def atest_script(self):
        s = get_sim_script('drcsim', '50.97.149.35')
        print(s)
        
    def test_launch(self):
        
        constellation_prefix = "02"
        launch_stage = None # use the current stage
        launch_stage = "nothing" #  
        #nothing
        #launch_stage = "os_reload"
        #init_router
        #init_privates
        #startup
        #configure
        #reboot
        #running
        
           
        
        self.constellation_name = 'test_vrc_contest_%s' % constellation_prefix 
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer  = get_softlayer_path()
        CONFIGURATION = 'vrc_contest'
        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name =  get_unique_short_name(test_name + "_")
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))

        constellation = ConstellationState( self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory", self.constellation_directory)
        constellation.set_value("configuration", 'vrc_contest')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        self.tags = {'TestCase':CONFIGURATION, 'configuration': CONFIGURATION, 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"}
        
        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)
        launch(self.username, self.constellation_name, constellation_prefix, self.credentials_softlayer, self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_softlayer, i)
            time.sleep(1)
        
        terminate(self.constellation_name, self.credentials_softlayer)

    def atest_monitor(self):

        self.constellation_name =  "cxf44f7040"
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer  = get_softlayer_path()

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
    
        
    def Xtest_router_ubuntu(self):
        directory = get_test_path('test_router_ubuntu')
        router_ip = '50.97.149.39'
        password = 'SapRekx3'
        os.makedirs(directory)
        print("add_ubuntu_user_to_router %s %s %s" % (router_ip, password, directory) )
        add_ubuntu_user_to_router(router_ip, password, directory)
        s = "ssh -i %s/key-router.pem ubuntu@%s" % (directory, router_ip)
        print(s)
    

        
    
    def stest_ubuntu_user_on_sim_from_router(self):
        
        constellation = ConstellationState( 'test_vrc_contest_toto')
        
        constellation_directory = constellation.get_value("constellation_directory")
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
        credentials_softlayer  = get_softlayer_path()
        osrf_creds = load_osrf_creds(credentials_softlayer)
        
        pub_ip, ip, password = get_machine_login_info(osrf_creds, "sim-01")
        log("setting up ubuntu user on simulator machine [%s / %s]" % (pub_ip,ip))
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
    unittest.main(testRunner = xmlTestRunner)       