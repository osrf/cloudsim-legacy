from __future__ import with_statement

import multiprocessing
from common.testing import get_boto_path, get_test_path
import unittest
from common.machine import get_unique_short_name, StdoutPublisher




def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
    
def find_machine(username, constellation, machine):
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(constellation, machine_name)
    return machine


def launch(username, constellation_name, tags, credentials_ec2, root_directory):

    from cloudsim import launch as cloudsim_launch
    from drc_sim_latest import launch as drc_sim_latest_launch
    from micro_vpn import launch as micro_vpn_launch

    
    log("team code one")
    sim_proc = multiprocessing.Process(target=micro_vpn_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory ))
    team_proc = multiprocessing.Process(target=cloudsim_launch, args=(username, constellation_name, tags,  credentials_ec2, root_directory ))
    
    sim_proc.start()
    team_proc.start()
    
    log("join")
    sim_proc.join()
    
    log("join")
    team_proc.join()
    
    
    log("done done")
    
    machines = {}
    machines['sim'] = find_machine(username, constellation_name, "micro_" + constellation_name)
    machines['team_code'] = find_machine(username, constellation_name, "cloudsim_" + constellation_name )
    return machines

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