from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile
import time

from common import StdoutPublisher, INSTALL_VPN, Machine2,\
    clean_local_ssh_key_entry, MachineDb
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
from common.startup_script_builder import ROS_SETUP_STARTUP_SCRIPT,\
    create_xorg_config_file, SOURCES_LIST_PRECISE, XGL_STARTUP_BEFORE,\
    XGL_STARTUP_AFTER


def get_launch_script():
    startup_script = """#!/bin/bash
# Exit on error
set -e

"""
    startup_script += 'date > /home/ubuntu/setup.log\n'
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list",file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'
    
    startup_script += 'echo "setup VPN" >> /home/ubuntu/setup.log\n'
    file_content = create_openvpn_server_cfg_file()
    startup_script += inject_file_into_script("openvpn.config",file_content)
    startup_script += INSTALL_VPN
    
    startup_script += 'echo "setup ROS" >> /home/ubuntu/setup.log\n'
    startup_script += ROS_SETUP_STARTUP_SCRIPT
    
#    startup_script += 'echo "setup X and gl" >> /home/ubuntu/setup.log\n'
#    startup_script += inject_file_into_script("/etc/X11/xorg.conf",file_content)
#    startup_script += XGL_STARTUP
#    file_content = create_xorg_config_file()
#    
    
    startup_script += 'echo "setup X and gl" >> /home/ubuntu/setup.log\n'
    startup_script += XGL_STARTUP_BEFORE
    
    startup_script += 'echo "create xorg.conf" >> /home/ubuntu/setup.log\n'
    file_content = create_xorg_config_file()
    startup_script += inject_file_into_script("/etc/X11/xorg.conf",file_content)
    
    startup_script += XGL_STARTUP_AFTER
    
    
    
    startup_script += 'echo "Setup complete" >> /home/ubuntu/setup.log\n'
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    return startup_script
    

def start_simualation():

def launch(username, machine_name, tags, publisher, credentials_ec2, root_directory):

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

    machine = Machine2(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     root_directory)
                     
    
    machine.create_ssh_connect_script()
    clean_local_ssh_key_entry(machine.config.ip )
    print("")
    print("")
    print("Waiting for ssh")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    
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
    
    print("Downloading key")
    remote_fname = "/etc/openvpn/static.key"
    machine.ssh_wait_for_ready(remote_fname)
    vpnkey_fname = os.path.join(machine.config.cfg_dir, "openvpn.key")
    machine.scp_download_file(vpnkey_fname, remote_fname)
    
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    print("creating %s" % fname_zip)
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(machine.config.uid, short_fname)
            fzip.write(fname, zip_name)
    
    print("Waiting for setup to complete")
    machine.ssh_wait_for_ready()

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
    unittest.main()            