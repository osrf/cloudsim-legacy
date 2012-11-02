from __future__ import with_statement
from __future__ import print_function


from launchers import launch
import os
import unittest
import uuid
from common import RedisPublisher
from common import StdoutPublisher
from common import MACHINES_DIR


from monitoring import sweep_monitor

username = "cloudsim_test@osrfoundation.org"

class Testo(unittest.TestCase):

    def test_launch_gazebo(self):
        
        machine_name = "gaz_" + str(uuid.uuid1())
        publisher = RedisPublisher(username)
        
        config_name = "gazebo"
        
        root_directory = "launch_test"
        ec2 = "/home/hugo/code/boto.ini"     
        
        launch(config_name, username, machine_name, publisher, ec2, root_directory)
    
    def atest_launch_micro(self):
        
        machine_name = str(uuid.uuid1())
        publisher = RedisPublisher(username)
        
        config_name = "gazebo"
        
        root_directory = "launch_test"
        ec2 = "/home/hugo/code/boto.ini"     
        
        launch(config_name, username, machine_name, publisher, ec2, root_directory)
        
            
    def atest_monitor(self):
        root_directory = "launch_test"
        publisher = RedisPublisher(username)
        sweep_monitor(root_directory)
        
    
    def test_terminate(self):
        print("TERMINATE? " )
    
if __name__ == "__main__":
    print("CLOUDSIMD tests")
    unittest.main()