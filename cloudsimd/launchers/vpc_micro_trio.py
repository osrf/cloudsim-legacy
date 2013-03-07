from __future__ import print_function

import unittest
import os
import time

import vpc_trio 

from launch_utils.launch import get_unique_short_name
from launch_utils.testing import get_test_runner
from launch_utils.testing import get_boto_path, get_test_path
from launch_utils.startup_scripts import get_vpc_router_script, get_vpc_open_vpn

CONFIGURATION = "vpc_micro_trio"


def get_micro_sim_script(routing_script):
    s = """#!/bin/bash
exec >/home/ubuntu/launch_stdout_stderr.log 2>&1

set -ex


""" +routing_script+"""

# Add ROS and OSRF repositories
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -
    
apt-get update
apt-get install -y cloudsim-client-tools

mkdir /home/ubuntu/cloudsim
mkdir /home/ubuntu/cloudsim/setup
touch /home/ubuntu/cloudsim/setup/done
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

"""
    return s

def get_micro_robot_script(routing_script):
    
    return get_micro_sim_script(routing_script)

def launch(username, constellation_name, tags, credentials_ec2, 
           constellation_directory ):

    routing_script = get_vpc_open_vpn(vpc_trio.OPENVPN_CLIENT_IP, 
                                      vpc_trio.TS_IP)
    
    ROBOT_AWS_TYPE  = 't1.micro'
    ROBOT_AWS_IMAGE = "ami-137bcf7a"
    ROBOT_SCRIPT = get_micro_robot_script(routing_script)
    
    SIM_AWS_TYPE  = 't1.micro'
    SIM_AWS_IMAGE = "ami-137bcf7a"
    SIM_SCRIPT = get_micro_sim_script(routing_script)

    
    ROUTER_AWS_TYPE='t1.micro'
    ROUTER_AWS_IMAGE="ami-137bcf7a"
    ROUTER_SCRIPT = get_vpc_router_script(vpc_trio.OPENVPN_SERVER_IP, 
                                          vpc_trio.OPENVPN_CLIENT_IP) 
    

    vpc_trio._launch(username, constellation_name, tags, credentials_ec2, 
                     constellation_directory,
                        ROUTER_AWS_TYPE,
                        ROUTER_AWS_IMAGE,
                        ROUTER_SCRIPT,
                        
                        ROBOT_AWS_TYPE,
                        ROBOT_AWS_IMAGE,
                        ROBOT_SCRIPT,
                        
                        SIM_AWS_IMAGE,
                        SIM_AWS_TYPE,
                        SIM_SCRIPT,
                        CONFIGURATION)

def monitor(username, constellation_name, credentials_ec2, counter):
    return vpc_trio._monitor(username, constellation_name, credentials_ec2, 
                             counter, CONFIGURATION)


def terminate(username, constellation_name, credentials_ec2, 
              constellation_directory):
    vpc_trio._terminate(username, constellation_name, credentials_ec2, 
                        constellation_directory, CONFIGURATION)
                           
    
def start_simulator(username, constellation, machine_name, package_name, 
                    launch_file_name, launch_args, ):
    vpc_trio.start_simulator(username, constellation, machine_name, 
                             package_name, launch_file_name, launch_args)

def stop_simulator(username, constellation, machine):
    vpc_trio.stop_simulator(username, constellation, machine)

class MicroTrioCase(unittest.TestCase):
    
    
    def test_trio(self):
        
        self.constellation_name =  get_unique_short_name("test_%s_" % CONFIGURATION)        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        
        self.tags = {'TestCase':CONFIGURATION, 
                     'configuration': CONFIGURATION, 
                     'constellation' : self.constellation_name, 
                     'user': self.username,
                     'GMT' : "not avail"}
        
        self.constellation_directory = os.path.abspath( os.path.join(get_test_path('test_trio'), self.constellation_name))
        print("creating: %s" % self.constellation_directory )
        os.makedirs(self.constellation_directory)
        
        launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.constellation_directory)
        
        sweep_count = 10
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       
