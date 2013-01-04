from __future__ import with_statement

import os
import multiprocessing
from common.testing import get_boto_path, get_test_path
import unittest
from common.machine import get_unique_short_name, find_machine
import time

from common import constants
import logging

def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
        logging.info(msg)
    except:
        print("[redis not installed]")
    print("launchers log> %s" % msg)
    



def launch(username, constellation_name, tags, credentials_ec2, root_directory, machine_name_param = None ):
    
    db_root_dir =os.path.dirname( os.path.dirname(root_directory))
    sim_machine_name = "simulator_" + constellation_name
    robot_machine_name = "robot_" + constellation_name
    
#    from cloudsim import launch as cloudsim_launch
#    from micro_vpn import launch as micro_vpn_launch
    
    from drc_sim_latest import launch as sim_launch
    from robot import launch as robot_launch
    
    
    log("robot_and_simulator launch")
#    sim_launch(username, constellation_name, tags,  credentials_ec2, root_directory, sim_machine_name )
    
    sim_proc = multiprocessing.Process(target= sim_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, sim_machine_name ))
    robot_proc = multiprocessing.Process(target=robot_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, robot_machine_name ))
#
    
    log("robot_proc start")
    robot_proc.start()
    
    log("sim_proc start")
    sim_proc.start()#
    
    time.sleep(10)
    
    log("sim_proc join")
    sim_proc.join()
    
    log("robot_proc join")
    robot_proc.join()
    
    sim_machine = find_machine(username, constellation_name, sim_machine_name, db_root_dir)
    robot_machine = find_machine(username, constellation_name, robot_machine_name, db_root_dir )
    
    zip_base_name = "%s.zip" % sim_machine_name
    sim_zip_fname = os.path.join(sim_machine.config.cfg_dir, zip_base_name)
    robot_machine.scp_send_file(sim_zip_fname, zip_base_name)
    
    robot_machine.ssh_send_command("unzip " + zip_base_name)
    log("copying sim.conf ")
    robot_machine.ssh_send_command("sudo cp " + os.path.join(sim_machine_name, constants.OPENVPN_CONFIG_FNAME) + " /etc/openvpn/sim.conf")
    log("copying key")
    robot_machine.ssh_send_command("sudo cp " + os.path.join(sim_machine_name, constants.OPENVPN_CLIENT_KEY_NAME) + " /etc/openvpn/")
    log("adding port")
    robot_machine.ssh_send_command("sudo sh -c 'echo lport 1195 >> /etc/openvpn/sim.conf'")
    log("restarting the openvpn service")
    robot_machine.ssh_send_command("sudo service openvpn restart")
    log("adding ros.sh to ~/.bashrc")
    robot_machine.ssh_send_command("echo . " + os.path.join("~", sim_machine_name, "ros.sh") + " >> ~/.bashrc")


class RobotAndSimulatorCase(unittest.TestCase):
    
    
    def test_launch(self):
        
        self.username = "toto@toto.com"
        self.constellation_name =  get_unique_short_name("test_tc1_")
     
       
        self.credentials_ec2  = get_boto_path()
        self.constellation_directory = "../../test_dir"
        self.tags = {'TestCases':'RobotAndSimulatorCase'}
        
        self.root_directory = get_test_path('RobotAndSimulatorCase')
        
        launch( self.username,
         self.constellation_name, 
         self.tags, 
         self.credentials_ec2, 
         self.root_directory)
        
        self.sim_machine = find_machine(self.username, self.constellation_name, "simulator_" +sim_machine_name, self.root_directory)
        self.robot_machine = find_machine(self.username, self.constellation_name, "robot_" + robot_machine_name, self.root_directory )
    
        ls = get_machine_tag(self.username, self.constellation_name, sim_machine.config.uid, "launch_state")
        self.assert_(ls == "running", "sim bad state")
        
        ls = get_machine_tag(self.username, self.constellation_name, robot_machine.config.uid, "launch_state")
        self.assert_(ls == "running", "robot bad state")
     
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate()
        self.sim.terminate()
        self.team.terminate()
        
if __name__ == "__main__":
    unittest.main()        