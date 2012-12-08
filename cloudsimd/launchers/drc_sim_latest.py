from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile
import time
import redis

from common import StdoutPublisher, INSTALL_VPN, Machine,\
    clean_local_ssh_key_entry, MachineDb, get_test_runner
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
from common.startup_script_builder import  ROS_SETUP_STARTUP_SCRIPT,\
    create_xorg_config_file, SOURCES_LIST_PRECISE, XGL_STARTUP_BEFORE,\
    XGL_STARTUP_AFTER
from common.machine import set_machine_tag

redis_client = redis.Redis()

def log(msg):
    print(msg)
    redis_client.publish("launchers", msg)

DRC_SETUP = """

echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | sudo apt-key add -

echo "package update" >> /home/ubuntu/setup.log
apt-get update

echo "install drc" >> /home/ubuntu/setup.log
apt-get install -y drcsim

echo "source drc setup from bashrc" >> /home/ubuntu/setup.log


"""

def get_launch_script():
    startup_script = """#!/bin/bash
# Exit on error
set -e
# Redirect everybody's output to a file
logfile=/home/ubuntu/launch_stdout_stderr.log
exec > $logfile 2>&1
"""
    startup_script += 'date > /home/ubuntu/setup.log\n'
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list",file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'
    startup_script += 'date > /home/ubuntu/setup.log\n'

    startup_script += 'echo "setup VPN" >> /home/ubuntu/setup.log\n'
    file_content = create_openvpn_server_cfg_file()
    startup_script += inject_file_into_script("openvpn.config",file_content)
    startup_script += INSTALL_VPN
    
    startup_script += 'echo "setup X and gl" >> /home/ubuntu/setup.log\n'
    startup_script += XGL_STARTUP_BEFORE
    
    startup_script += 'echo "create xorg.conf" >> /home/ubuntu/setup.log\n'
    file_content = create_xorg_config_file()
    startup_script += inject_file_into_script("/etc/X11/xorg.conf",file_content)
    
    startup_script += XGL_STARTUP_AFTER
    
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    
    startup_script += 'echo "setting drc / ros  package repo" >> /home/ubuntu/setup.log\n'
    startup_script += DRC_SETUP
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    
    startup_script += 'echo "Setup complete" >> /home/ubuntu/setup.log\n'
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    return startup_script
    

def launch(username, constellation_name, tags, publisher, credentials_ec2, root_directory):

    startup_script = get_launch_script()
    
    config = Machine_configuration()
    config.initialize(   image_id = "ami-98fa58f1",  
                         instance_type = 'cg1.4xlarge', # 'm1.small' , 
                         security_groups = ['openvpn'],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=1000)
    
    machine_name = "simulator_" + constellation_name
    
    domain = username.split("@")[1]
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "waiting for ip")
    set_machine_tag(domain, constellation_name, machine_name, "up", True)
    
    machine = Machine(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     root_directory)

    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "booting up")
    machine.create_ssh_connect_script()
    clean_local_ssh_key_entry(machine.config.ip )

    log("Waiting for ssh")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "preparing keys")
    fname_vpn_cfg = os.path.join(machine.config.cfg_dir, "openvpn.config")
    file_content = create_openvpn_client_cfg_file(machine.config.hostname)
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    fname_start_vpn = os.path.join(machine.config.cfg_dir, "start_vpn.sh")    
    file_content = create_vpn_connect_file()
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)

    fname_ros = os.path.join(machine.config.cfg_dir, "ros.sh")    
    file_content = create_ros_connect_file()
    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    fname_ssh_key =  os.path.join(machine.config.cfg_dir, machine.config.kp_name + '.pem')
    fname_ssh_sh =  os.path.join(machine.config.cfg_dir,'ssh.sh')
    
    fname_zip = os.path.join(machine.config.cfg_dir, "%s.zip" % machine.config.uid)
    
    log("Downloading key")
    remote_fname = "/etc/openvpn/static.key"
    machine.ssh_wait_for_ready(remote_fname)
    vpnkey_fname = os.path.join(machine.config.cfg_dir, "openvpn.key")
    machine.scp_download_file(vpnkey_fname, remote_fname)
    
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    log("creating %s" % fname_zip)
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(machine.config.uid, short_fname)
            fzip.write(fname, zip_name)
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "installing packages")
    log("Waiting for setup to complete")
    machine.ssh_wait_for_ready()
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "rebooting")
    log("rebooting machine")
    machine.reboot()
    
    log("waiting for machine to be up again")
    # machine.get_aws_status(timeout)['state'] == 'running'
    machine.ssh_wait_for_ready("/home/ubuntu")
    log("machine ready")
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "running")

class TestCases(unittest.TestCase):
    
   
    def test_script(self):
        script = get_launch_script()
        print (script)
        
    
    def atest_launch(self):
        
        username = "toto@toto.com"
        machine_name = "gazebo_" + str(uuid.uuid1())
        publisher = StdoutPublisher()
        launch(username, machine_name, publisher)
        
        

if __name__ == "__main__":
    unittest.main(testRunner = get_runner())               