from __future__ import with_statement
from __future__ import print_function


from launchers import launch, terminate, start_simulator, stop_simulator
import os
import unittest
import uuid


from common import StdoutPublisher
from common import MACHINES_DIR


from monitoring import sweep_monitor
import time
from common.testing import kill_all_ec2_instances, get_boto_path, get_test_path
from common.machine import create_ec2_proxy, get_unique_short_name,\
    get_machine_tag


username = "cloudsim_test@osrfoundation.org"

class DrcSimLatestTestCase(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)

    def test_start_stop_simulation(self):
        
        self.package_name = "drc_robot_utils"
        self.launch_file_name = "drc_robot.launch"
        self.launch_args= ""
                      
        self.username = "test@osrfoundation.org" 
        self.constellation_name = "test_launch_drcim_latest_" + get_unique_short_name()
        self.ec2 = get_boto_path()
        
        tags = {"test":"test_launch_drcim_latest"} 
        
        self.root_directory = get_test_path('Test_launch_drcim_latest')
        
       
        self.machine = launch(self.username, 
                              "drc_sim_latest", 
                              self.constellation_name, 
                              self.ec2, 
                              self.root_directory)
        
        self.machine_name  = self.machine.config.uid
        
        try:
            import redis
            ls = get_machine_tag(self.username, self.constellation_name, self.machine_name, "launch_state")
            self.assert_(ls == "running", "bad state")
        except:
            print("no redis")
            
        time.sleep(20)
        x = self.machine.get_X_status()
        self.assert_(x, "no openGL")
        
        start_simulator(self.username, 
                       self.constellation_name,
                       self.machine_name, 
                       self.package_name, 
                       self.launch_file_name,
                       self.launch_args,
                       self.root_directory)
        
        time.sleep(20)
        s = self.machine.get_gazebo_status()
        self.assert_(s, "no simulator")
        
        stop_simulator(self.username, self.constellation_name, self.machine_name, self.root_directory)
        time.sleep(10)
        s = self.machine.get_gazebo_status()
        self.assert_(s==False, "simulator did not stop")
        
        terminate(self.username, self.constellation_name, self.ec2, self.root_directory)
        time.sleep(10)
        c = self.machine.get_aws_status()
        self.assert_(d['state'] == "shutting-down", "Not shutting down")
        
        
        
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate()
        
        ec2 = create_ec2_proxy(get_boto_path())
        kill_all_ec2_instances(ec2)
    

class MicroTestCase(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.machine = None

    def atest_start_stop_micro(self):
        
        
        self.username = "test@osrfoundation.org" 
        self.constellation_name = "test_MicroTestCase_" + get_unique_short_name()
        self.ec2 = get_boto_path()
        
        tags = {"test":"MicroTestCase"} 
        
        self.root_directory = get_test_path('MicroTestCase')
        
        self.publisher = StdoutPublisher()
        
        
        self.machine = launch(self.username, 
                              "micro_vpn", 
                              self.constellation_name, 
                              self.ec2, 
                              self.root_directory,
                              self.publisher)
        
        self.machine_name  = self.machine.config.uid
        
        time.sleep(5)
        
        v = self.machine.get_deb_package_version("cloudsim-client-tools")
        print("cloudsim-client-tools version %s" % v)
        self.assert_(v.find("No packages found matching") == -1, "client tools not installed" )
       
        
        time.sleep(10)
        c = self.machine.get_aws_status()
        self.assert_(d['state'] == "shutting-down", "Not shutting down")
        
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        terminate(self.username, self.constellation_name, self.publisher, self.ec2, self.root_directory)
        
        #ec2 = create_ec2_proxy(get_boto_path())
        #kill_all_ec2_instances(ec2)
        
    
if __name__ == "__main__":
    print("CLOUDSIMD tests")
    from common.testing import get_test_runner
    unittest.main(testRunner =  get_test_runner()) 