from __future__ import with_statement

import multiprocessing
from common.testing import get_boto_path
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
    
    
def launch(username, constellation_name, tags, publisher, credentials_ec2, root_directory):

    from cloudsim import launch as cloudsim_launch
    from drc_sim_latest import launch as drc_sim_latest_launch
    from micro_vpn import launch as micro_vpn_launch

    
    log("team code one")
    sim_proc = multiprocessing.Process(target=micro_vpn_launch, args=(username, constellation_name, tags, publisher, credentials_ec2, root_directory ))
    team_proc = multiprocessing.Process(target=cloudsim_launch, args=(username, constellation_name, tags, publisher, credentials_ec2, root_directory ))
    
    sim_proc.start()
    team_proc.start()
    
    log("join")
    sim_proc.join()
    
    log("join")
    team_proc.join()
    
    
    log("done done")
    
    machines = {}
    machines['sim'] = None
    machines['team_code'] = None
    return machines

class TestCases(unittest.TestCase):
    
    
    def test_micro(self):
        
        username = "toto@toto.com"
        constellation_name =  get_unique_short_name("test_tc1_")
        publisher = StdoutPublisher()
       
        credentials_ec2  = get_boto_path()
        constellation_directory = "../../test_dir"
        tags = {'TestCases':'team_code_one'}
        
        launch("toto@toto.com", 
         constellation_name, 
         tags, 
         publisher, 
         credentials_ec2, 
         constellation_directory)
        

if __name__ == "__main__":
    unittest.main()        