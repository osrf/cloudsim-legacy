from __future__ import with_statement
from __future__ import print_function

import os

from constants import MACHINES_DIR, BOTO_CONFIG_FILE_USEAST, OV_SERVER_IP, OV_CLIENT_IP, OPENVPN_STATIC_KEY_FNAME

from machine import Machine2
from machine_configuration import Machine_configuration
import unittest

STARTUP_SCRIPT = """#!/bin/bash
# Exit on error
set -e

# Overwrite the sources.list file with different content
cat <<DELIM > /etc/apt/sources.list
%s
DELIM

apt-get update

# install X, with nvidia drivers
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` nvidia-current nvidia-current-dev gnome-session-fallback

# configure X
cat <<DELIM > /etc/X11/xorg.conf
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
    BusID          "PCI:0:3:0"
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

# setup auto xsession login
echo "
[SeatDefaults]
greeter-session=unity-greeter
autologin-user=%s
autologin-user-timeout=0
user-session=gnome-fallback
" > /etc/lightdm/lightdm.conf
initctl stop lightdm || true
initctl start lightdm 

# Install ROS.
# For now, just pull Gazebo from Fuerte.  In the future, give 
# options here.
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
wget http://packages.ros.org/ros.key -O - | apt-key add -
apt-get update
apt-get -y install ros-fuerte-pr2-simulator ros-fuerte-arm-navigation ros-fuerte-pr2-teleop-app ros-fuerte-pr2-object-manipulation ros-fuerte-pr2-navigation

# Install and start openvpn.  Do this last, because we're going to 
# infer that the machine is ready from the presence of the 
# openvpn static key file.
apt-get install -y openvpn
openvpn --genkey --secret %s
cat <<DELIM > openvpn.config
dev tun
ifconfig %s %s
secret %s
DELIM
chmod 644 %s
# Set up for autostart by dropping this stuff in /etc/openvpn
cp openvpn.config /etc/openvpn/openvpn.conf
cp %s /etc/openvpn/%s
service openvpn start
"""

def generate_startup_script(username, distro, machine_id, server_ip, client_ip):
    data_dir = os.path.join(os.path.split(__file__)[0], '../data')
    
    sources_list = open('%s/sources.list-%s'%(data_dir, distro )).read()
    
    key = OPENVPN_STATIC_KEY_FNAME
    startup_script = STARTUP_SCRIPT % (sources_list, username, key, server_ip, client_ip, key, key, key, key)
    return startup_script




class Config_case(unittest.TestCase):

    def get_config_dir(self):
        config_dir = os.path.join(os.path.split(__file__)[0], '../../../distfiles/configs')
        self.assert_(os.path.exists(config_dir), '%s does not exist' % config_dir)
        return config_dir
    
    def get_config_fname(self, cfg_name):
        config_dir = self.get_config_dir()
        fname = os.path.join(config_dir, cfg_name)
        return fname
    
    def test_make_configs(self):
        
        username = 'ubuntu'
        distro = 'precise'
        startup_script = generate_startup_script(username, distro, username, OV_SERVER_IP, OV_CLIENT_IP)
        
        config = Machine_configuration()
        config.initialize(image_id ="ami-98fa58f1", 
                     instance_type = 'cg1.4xlarge' , 
                     security_groups = ['openvpn'], 
                     username = username, 
                     distro = distro,
                     startup_script = startup_script,
                     ip_retries = 200,
                     ssh_retries= 800)
        
       
        fname = self.get_config_fname('simulation_gpu')
        print("Saving to '%s'" % fname)
        config.save_json(fname)

    def test_make_image_config(self):
        
        username = 'ubuntu'
        distro = 'precise'
        startup_script = ""
        
        config = Machine_configuration()
        config.initialize(image_id ="ami-e560dc8c", 
                     instance_type = 'cg1.4xlarge' , 
                     security_groups = ['openvpn'], 
                     username = username, 
                     distro = distro,
                     startup_script = startup_script,
                     ip_retries = 200,
                     ssh_retries= 800)
        
       
        fname = self.get_config_fname('simulation_gpu_ami')
        print("Saving to '%s'" % fname)
        config.save_json(fname)
        
    def atest_start_stop(self):
            
            fname = self.get_config_fname('simulation_gpu')
            config = Machine_configuration.from_file(fname)
            
            config.print_cfg()
            
            root_directory = "tests"
            
            simulator  = Machine2(config, 
                                  tags= {'type':'test'}, 
                                  credentials_ec2 = '../../../../boto.ini', 
                                  root_directory = "test_machines" )
            
            fname = '%s/machine.instance' % config.root_directory
            print('saving machine instance info to "%s"'%fname)
            simulator.config.save_json(fname)
            
            # simulator = Machine2.from_file(fname)
            print("Machine launched at: %s"%(simulator.config.hostname))
            print("\nIn case of emergency:\n\n%s\n\n"%(simulator.user_ssh_command()))
            print("Waiting for ssh")
            
            simulator.ssh_wait_for_ready()
            print("Good to go.")            

            simulator.terminate()
            # commands.getoutput('rm -rf %s' % data_dir)

    def test_start_stop_gpu_ami(self):
           
            fname = self.get_config_fname('simulation_gpu_ami')
            config = Machine_configuration.from_file(fname)
            
            config.print_cfg()
            
            root_directory = "tests"
            
            simulator  = Machine2(config, 
                                  tags= {'type':'test'}, 
                                  credentials_ec2 = '../../../../boto.ini', 
                                  root_directory = "test_machines" )
            
            fname = '%s/machine.instance' % config.root_directory
            print('saving machine instance info to "%s"'%fname)
            simulator.config.save_json(fname)
            
            # simulator = Machine2.from_file(fname)
            print("Machine launched at: %s"%(simulator.config.hostname))
            print("\nIn case of emergency:\n\n%s\n\n"%(simulator.user_ssh_command()))
            print("Waiting for ssh")
            
            simulator.ssh_wait_for_ready()
            print("Good to go.")            

     #       simulator.terminate()
            # commands.getoutput('rm -rf %s' % data_dir)
      
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()      