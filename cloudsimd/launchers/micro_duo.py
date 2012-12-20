from __future__ import with_statement

import multiprocessing
from common.testing import get_boto_path, get_test_path
import unittest
from common.machine import get_unique_short_name, find_machine
import time
import os
from common import constants



def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
    



def launch(username, constellation_name, tags, credentials_ec2, root_directory, machine_name_param = None ):
    
    
    sim_machine_name = "simulator_" + constellation_name
    robot_machine_name = "robot_" + constellation_name
    db_root_dir =os.path.dirname( os.path.dirname(root_directory))
    # router_machine_name = "router_" + constellation_name
    
#    from cloudsim import launch as cloudsim_launch
    from micro_sim import launch as simulator_launch
    from micro_robot import launch as robot_launch
    
    #from drc_sim_latest import launch as drc_sim_latest_launch
    #from robot import launch as robot_launch
    
    
    log("team code one")
#    sim_launch(username, constellation_name, tags,  credentials_ec2, root_directory, sim_machine_name )
    
    #sim_proc = multiprocessing.Process(target= drc_sim_latest_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, sim_machine_name ))
    #robot_proc = multiprocessing.Process(target=robot_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, robot_machine_name ))
        
    sim_proc = multiprocessing.Process(target= simulator_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, sim_machine_name ))
    robot_proc = multiprocessing.Process(target= robot_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, robot_machine_name ))
    # router_proc = multiprocessing.Process(target= micro_vpn_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory, router_machine_name ))
    
    log("sim_proc start")
    sim_proc.start()
    
    log("robot_proc start")
    robot_proc.start()
    
    time.sleep(30)
    
    log("sim_proc join")
    sim_proc.join()
    
    log("robot_proc join")
    robot_proc.join()
    
    log("all joined")
    log("micro_duo launch done")

    
    sim_machine = find_machine(username, constellation_name, sim_machine_name, db_root_dir)
    robot_machine = find_machine(username, constellation_name, robot_machine_name, db_root_dir )
    
    zip_base_name = "%s.zip" % sim_machine_name
    sim_zip_fname = os.path.join(sim_machine.config.cfg_dir, zip_base_name)
    robot_machine.scp_send_file(sim_zip_fname, zip_base_name)
    
    robot_machine.ssh_send_command("unzip " + zip_base_name)
    robot_machine.ssh_send_command("sudo cp " + os.path.join(sim_machine_name, constants.OPENVPN_CONFIG_FNAME) + " /etc/openvpn/sim.conf")
    robot_machine.ssh_send_command("sudo cp " + os.path.join(sim_machine_name, constants.OPENVPN_CLIENT_KEY_NAME) + " /etc/openvpn/")
    robot_machine.ssh_send_command("sudo sh -c 'echo lport 1195 >> /etc/openvpn/sim.conf'")
    robot_machine.ssh_send_command("sudo service openvpn restart")
    robot_machine.ssh_send_command("echo . " + os.path.join("~", sim_machine_name, "ros.sh") + " >> ~/.bashrc")


    # sim_zip_fname = os.path.join(machine.config.cfg_dir, "%s.zip" % sim_machine.config.uid)
    # router_machine = find_machine(username, constellation_name, router_machine_name )



class TeamCodeCase(unittest.TestCase):
    
    
    def test_micro(self):
        
        self.username = "toto@toto.com"
        self.constellation_name =  get_unique_short_name("test_tc1_")
     
       
        self.credentials_ec2  = get_boto_path()
        self.constellation_directory = "../../test_dir"
        self.tags = {'TestCases':'TeamCodeCase'}
        
        self.root_directory = get_test_path('test_team_code')
        
        self.sim, self.team = launch( self.username,
         self.constellation_name, 
         self.tags, 
         self.credentials_ec2, 
         self.root_directory)
        
        ls = get_machine_tag(self.username, self.constellation_name, self.sim.config.uid, "launch_state")
        self.assert_(ls == "running", "bad state")
        
        ls = get_machine_tag(self.username, self.constellation_name, self.team.config.uid, "launch_state")
        self.assert_(ls == "running", "bad state")
     
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate()
        self.sim.terminate()
        self.team.terminate()
        
if __name__ == "__main__":
    unittest.main()        