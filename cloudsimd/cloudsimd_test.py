from __future__ import with_statement
from __future__ import print_function


from launchers import launch, terminate
import os
import unittest
import uuid
from common import RedisPublisher
from common import StdoutPublisher
from common import MACHINES_DIR


from monitoring import sweep_monitor

username = "cloudsim_test@osrfoundation.org"

class Testo(unittest.TestCase):

    def atest_launch_gazebo(self):
        
        machine_name = "gaz_" + str(uuid.uuid1())
        publisher = RedisPublisher(username)
        
        config_name = "gazebo"
        
        root_directory = "launch_test"
        ec2 = "/home/hugo/code/boto.ini"     
        
        launch(config_name, username, machine_name, publisher, ec2, root_directory)
    
    def test_launch_micro(self):
        
        machine_name = str(uuid.uuid1())
        publisher = RedisPublisher(username)
        
        config_name = "micro_vpn"
        
        root_directory = "launch_test"
        ec2 = "/home/hugo/code/boto.ini"     

        
        launch( username, config_name, machine_name, publisher, ec2, root_directory)
        
        terminate( username, machine_name, publisher, ec2, root_directory)
        
    def atest_monitor(self):
        root_directory = "launch_test"
        publisher = RedisPublisher(username)
        sweep_monitor(root_directory)
        
    def ztest_terminate(self):
        print("TERMINATE? " )
        publisher = RedisPublisher(username)
        terminate( 'username@bobo.com', 'machine_name', publisher, 'ec2', 'root_directory')
    
    def test_start_simulator(self):
        machine = "machine"
        OV_SERVER_IP = "10.1.1.1"
        DISPLAY = "0"
        
        server_ip = OV_SERVER_IP
        display = DISPLAY 
        package= "ROSPACK"
        launchfile= "launch"
        launchargs= "args"
        script = '". /opt/ros/fuerte/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s %s  >/dev/null 2>/dev/null </dev/null &"'%(server_ip, display, package, launchfile, launchargs)
        
        print (script)
    
    
if __name__ == "__main__":
    print("CLOUDSIMD tests")
    unittest.main()