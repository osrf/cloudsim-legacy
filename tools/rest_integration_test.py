#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import unittest
import time

# add cloudsim directory to sytem path
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)
print("sys.path: %s" % sys.path)


from cloudsimd.launchers.cloudsim import create_cloudsim, terminate
from cloudsimd.launchers.launch_utils.launch_db import ConstellationState
from cloudsimd.launchers.launch_utils.launch_db import get_unique_short_name
from cloudsimd.launchers.launch_utils.testing import get_test_runner


def diff(a, b):
    """
    Compares 2 lists and returns the elements in list a only  
    """
    b = set(b)
    return [aa for aa in a if aa not in b]

def launch_constellation(api, config):
    api.launch_constellation("aws", "Simulator")
    
    time.sleep(30)
    
    
    # we're about to create a new constellation... this may not 
    # be the first
    previous_constellations = [x['constellation_name'] \
                               for x in api.get_constellations()]
    found = False
    count = 0
    constellation_name = None
    while not found:
        count += 1
        if count > 100:
            return None
        
        constellation_list = api.get_constellations()
        current_names = [x['constellation_name'] \
                               for x in constellation_list]
        
        new_constellations = diff(current_names, previous_constellations)
        print ("new constellations: %s" % new_constellations)
        if len(new_constellations) > 0:
             found = True
             constellation_name = new_constellations[0]
    
    count = 0
    ready = False
    while not ready:
        count += 1
        if count > 100:
            api.terminate_constellation(constellation_name)
            return None

        const_data = api.get_constellation_data(constellation_name)
        state = const_data['constellation_state']
        print("%s state: %s" % (constellation_name, state))
        if state == "running":
            return  const_data
    
    

class RestTest(unittest.TestCase):

    def setUp(self):
        print("setUp")
        
        self.user = 'admin'
        self.password = 'test123'
        
        from launch_utils.testing import get_boto_path
        from launch_utils.testing import get_test_path

        self.name = get_unique_short_name('rst')
        self.data_dir = get_test_path("rest_test")

        self.ip = create_cloudsim(username=self.user,
                                  credentials_fname=get_boto_path(),
                                  configuration="CloudSim-stable",
                                  authentication_type="Basic",
                                  password=self.password,
                                  data_dir=self.data_dir,
                                  constellation_name=self.name)
        print("cloudsim %s created" % self.ip)
    
    
    def test(self):
        print("test")
        api = CloudSimRestApi(self.ip, self.user, self.password)    
        

    def tearDown(self):
        print("terminate cloudsim %s" % self.ip)
        terminate(self.name)
        constellation = ConstellationState(self.name)
        constellation.expire(1)

if __name__ == "__main__":
   
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)