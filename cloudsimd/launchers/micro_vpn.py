from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile

from common import StdoutPublisher, INSTALL_VPN, Machine,\
    clean_local_ssh_key_entry, MachineDb
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
import time
import boto
from common.machine import set_machine_tag

#def launchx():
#    print ("launch from micro_vpn")
    

def log(msg):
    try:
        import redis
        red = redis.Redis()
        red.publish("launchers", msg)
    except:
        pass
    print(msg)
        

def launch(username, 
           constellation_name, 
           tags, publisher, credentials_ec2, 
           constellation_directory):

    startup_script = """#!/bin/bash
# Exit on error
set -e

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
    
    file_content = create_openvpn_server_cfg_file()
    startup_script += inject_file_into_script("openvpn.config",file_content)

    startup_script += INSTALL_VPN
    log(startup_script)

    config = Machine_configuration()
    config.initialize(   image_id ="ami-137bcf7a", 
                         instance_type = 't1.micro', # 'm1.small' , 
                         security_groups = ['ping_ssh'],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=200)
    
    machine_name = "micro_" + constellation_name
    
    domain = username.split("@")[1]
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "waiting for ip")
    set_machine_tag(domain, constellation_name, machine_name, "up", True)
    
    machine = Machine(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     constellation_directory)
                     
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "booting up")
    
    machine.create_ssh_connect_script()
    clean_local_ssh_key_entry(machine.config.ip )

    log("Waiting for ssh")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    log("Waiting for packages to be installed")
    machine.ssh_wait_for_ready()
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "preparing keys")
    log("Downloading key")
    remote_fname = "/etc/openvpn/static.key"
    
    fname_vpn_cfg = os.path.join(machine.config.cfg_dir, "openvpn.config")
    file_content = create_openvpn_client_cfg_file(machine.config.hostname)
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    fname_start_vpn = os.path.join(machine.config.cfg_dir, "start_vpn.sh")    
    file_content = create_vpn_connect_file()
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)

    vpnkey_fname = os.path.join(machine.config.cfg_dir, "openvpn.key")
    machine.scp_download_file(vpnkey_fname, remote_fname)

    fname_ros = os.path.join(machine.config.cfg_dir, "ros.sh")    
    file_content = create_ros_connect_file()
    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    fname_ssh_key =  os.path.join(machine.config.cfg_dir, machine.config.kp_name + '.pem')
    fname_ssh_sh =  os.path.join(machine.config.cfg_dir,'ssh.sh')
    fname_zip = os.path.join(machine.config.cfg_dir, "%s.zip" % machine.config.uid)
    
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
            
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "rebooting")        
    log("rebooting machine")
    r = machine.reboot()
    
    log("waiting for machine to be up again")
    # machine.get_aws_status(timeout)['state'] == 'running'
    machine.ssh_wait_for_ready("/home/ubuntu")
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "running")
    
class TestCases(unittest.TestCase):
    
    
    def test_micro(self):
        
        username = "toto@toto.com"
        constellation_name = "test_microvpn_" + str(uuid.uuid1())
        publisher = StdoutPublisher()
       
        credentials_ec2  = "/home/hugo/code/boto.ini"
        constellation_directory = "../../test_dir"
        tags = {'TestCases':'micro_vpn'}
        
        launch("toto@toto.com", 
         constellation_name, 
         tags, 
         publisher, 
         credentials_ec2, 
         constellation_directory)
        

if __name__ == "__main__":
    unittest.main()            