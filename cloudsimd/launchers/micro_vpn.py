from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile

from machine import StdoutPublisher, INSTALL_VPN, Machine2,\
    clean_local_ssh_key_entry, MachineDb
from startup_script_builder import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from machine_configuration import Machine_configuration
import time

#def launchx():
#    print ("launch from micro_vpn")
    


    
def launch(username, machine_name, tags, publisher, credentials_ec2, root_directory):


     
    startup_script = """#!/bin/bash
# Exit on error
set -e

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
    
    
    
    file_content = create_openvpn_server_cfg_file()
    startup_script += inject_file_into_script("openvpn.config",file_content)

    startup_script += INSTALL_VPN
    print(startup_script)

    config = Machine_configuration()
    config.initialize(   image_id ="ami-137bcf7a", 
                         instance_type = 't1.micro', # 'm1.small' , 
                         security_groups = ['ping_ssh'],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=200)

    micro = Machine2(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     root_directory)
                     
    
    micro.create_ssh_connect_script()
    clean_local_ssh_key_entry(micro.config.ip )
    print("")
    print("")
    print("Waiting for ssh")
    micro.ssh_wait_for_ready("/home/ubuntu")
    
    print("Waiting for setup to complete")
    micro.ssh_wait_for_ready()
    
    print("Downloading key")
    remote_fname = "/etc/openvpn/static.key"
    
    fname_vpn_cfg = os.path.join(micro.config.cfg_dir, "openvpn.config")
    file_content = create_openvpn_client_cfg_file(micro.config.hostname)
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    fname_start_vpn = os.path.join(micro.config.cfg_dir, "start_vpn.sh")    
    file_content = create_vpn_connect_file()
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)

    vpnkey_fname = os.path.join(micro.config.cfg_dir, "openvpn.key")
    micro.scp_download_file(vpnkey_fname, remote_fname)

    fname_ros = os.path.join(micro.config.cfg_dir, "ros.sh")    
    file_content = create_ros_connect_file()
    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    fname_ssh_key =  os.path.join(micro.config.cfg_dir, micro.config.kp_name + '.pem')
    fname_ssh_sh =  os.path.join(micro.config.cfg_dir,'ssh.sh')
    fname_zip = os.path.join(micro.config.cfg_dir, "%s.zip" % micro.config.uid)
    
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    print("creating %s" % fname_zip)
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(micro.config.uid, short_fname)
            fzip.write(fname, zip_name)
            

class TestCases(unittest.TestCase):
    
   
    
    def test_micro(self):
        
        username = "toto@toto.com"
        machine_name = "microvpn_" + str(uuid.uuid1())
        publisher = StdoutPublisher()
        launch(username, machine_name, publisher)
        
        

if __name__ == "__main__":
    unittest.main()            