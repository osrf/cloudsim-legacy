#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import unittest
import time
import datetime


from cloudsim_rest_api import CloudSimRestApi

# add cloudsim directory to sytem path
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)
# print("sys.path: %s" % sys.path)

import cloudsimd.launchers.cloudsim as cloudsim
from cloudsimd.launchers.launch_utils.launch_db import ConstellationState
from cloudsimd.launchers.launch_utils.launch_db import get_unique_short_name
from cloudsimd.launchers.launch_utils.testing import get_test_runner


CLOUDSIM_CONFIG = "CloudSim-stable"
SIM_CONFIG = "Simulator-stable"


class RestException(Exception):
    pass

def diff(a, b):
    """
    Compares 2 lists and returns the elements in list a only  
    """
    b = set(b)
    return [aa for aa in a if aa not in b]


def launch_constellation(api, config, max_count=100):
    # we're about to create a new constellation... this may not 
    # be the first
    previous_constellations = [x['constellation_name'] \
                               for x in api.get_constellations()]
    api.launch_constellation("aws", config)
    print("waiting 10 secs")
    time.sleep(10)

    found = False
    count = 0
    constellation_name = None
    while not found:
        count += 1
        if count > max_count:
            raise RestException("Timeout in Launch %s" % config)
        
        constellation_list = api.get_constellations()
        current_names = [x['constellation_name'] \
                               for x in constellation_list]
        
        new_constellations = diff(current_names, previous_constellations)
        print ("%s/%s) new constellations: %s" % (count,
                                                  max_count,
                                                  new_constellations))
        if len(new_constellations) > 0:
             found = True
             constellation_name = new_constellations[0]
    return constellation_name


def wait_for_state(api,
                   constellation_name,
                   key="constellation_state",
                   value="running",
                   max_count=100,
                   sleep_secs=5):
    count = 0
    while True:
        time.sleep(sleep_secs)
        count += 1
        if count > max_count:
            raise RestException("Timeout in wait for %s = %s "
                                " for %s" % (key, value, constellation_name))

        const_data = api.get_constellation_data(constellation_name)
        state = const_data[key]
        print("%s/%s) %s [%s] = %s" % (count,
                                     max_count,
                                     constellation_name,
                                     key,
                                     state))
        if state == value:
            return  const_data


class Testo(unittest.TestCase):
    
    def test(self):
        print("Testo")


def _get_now_str(days_offset=0):
    """
    Returns a utc string date time format of now, with optional
    offset.
    """
    dt = datetime.timedelta(days=days_offset)
    now = datetime.datetime.utcnow()
    t = now - dt
    s = t.isoformat()
    return s


def create_task(cloudsim_api, constellation_name, task_dict):
    """
    Creates a new task and retrieves the id of the new task. This 
    requires comparing task names before and after creation 
    """
    def task_names():
        const_data = cloudsim_api.get_constellation_data(constellation_name)
        task_names = [x['task_id'] for x in const_data['tasks']]
        return task_names
    
    previous_tasks = task_names()
    cloudsim_api.create_task(constellation_name, task_dict)
    new_tasks = task_names()
    
    delta_tasks = diff(new_tasks, previous_tasks)
    new_task_id = delta_tasks[0]
    return new_task_id
    
    
def run_task(cloudsim_api, constellation_name, task_id,
               max_count=100,
               sleep_secs=1):
    """
    Starts a task and waits for its status to be "running"
    """
    # check task
    task_dict = cloudsim_api.read_task(constellation_name, task_id)
    state = task_dict['task_state']
    if state != "ready":
        raise RestException("Can't start task in state %s" % state)
    
    # run task
    cloudsim_api.start_task(constellation_name, task_id)
    
    # wait until the task is running
    count = 0
    while True:
        time.sleep(sleep_secs)
        count += 1
        if count > max_count:
            raise RestException("Timeout in start_task"
                                "%s for %s" % (task_id, constellation_name))    
        task_dict = cloudsim_api.read_task(constellation_name, task_id)
        print("%s/%s Task %s: %s" % (count, max_count, task_id, task_dict['task_state']))
        if task_dict['task_state'] == 'running':
            return

def create_task_dict(launch_file='vrc_taks_1.launch'):
        task_dict = {}
        task_dict['task_title'] = 'test task'
        task_dict['ros_package'] = 'atlas_utils'
        task_dict['launch_file'] = launch_file
        task_dict['launch_args'] = ''
        task_dict['timeout'] = '3600'
        task_dict['latency'] = ''
        task_dict['uplink_data_cap'] = ''
        task_dict['downllink_data_cap'] = ''
        task_dict['local_start'] = _get_now_str(-1)  # yesterday
        task_dict['local_stop'] = _get_now_str(1)    # tomorrow
        task_dict['vrc_id'] = 1
        task_dict['vrc_num'] = 1
        return task_dict

class RestTest(unittest.TestCase):

    def setUp(self):
        print("setUp")
        
        self.cloudsim_api = None
        self.simulator_name = None
        self.papa_cloudsim_name = None
        
        self.user = 'admin'
        self.password = 'test123'
        
        from launch_utils.testing import get_boto_path
        from launch_utils.testing import get_test_path

        self.papa_cloudsim_name = get_unique_short_name('rst')
        self.data_dir = get_test_path("rest_test")
        
        self.ip = cloudsim.create_cloudsim(username=self.user,
                                  credentials_fname=get_boto_path(),
                                  configuration=CLOUDSIM_CONFIG,
                                  authentication_type="Basic",
                                  password=self.password,
                                  data_dir=self.data_dir,
                                  constellation_name=self.papa_cloudsim_name)
        print("papa cloudsim %s created in %s" % (self.ip, self.data_dir))

    def test(self):
        print("test")
        self.cloudsim_api = CloudSimRestApi(self.ip, self.user, self.password)    
        self.simulator_name = launch_constellation(self.cloudsim_api, 
                                                   config=SIM_CONFIG)
        print("Simulator %s launched" % (self.simulator_name))
        # wait_for_state(self.cloudsim_api, self.simulator_name)
        wait_for_state(self.cloudsim_api,
                       self.simulator_name,
                       key="launch_stage", 
                       value="running",
                       max_count=100)
        
        print("CloudSim %s ready" % self.ip)
        print("Simulator %s is running" % self.simulator_name)
        # the simulator is ready!
        
        # add a task
        task_dict = create_task_dict()
        self.task_id = create_task(self.cloudsim_api,
                                   self.simulator_name,
                                   task_dict)

        run_task(self.cloudsim_api,self.simulator_name, self.task_id)


    def tearDown(self): 
        # terminate simulator
        try:
            if self.cloudsim_api and self.simulator_name:
                self.cloudsim_api.terminate_constellation(self.simulator_name)
        except Exception, e:
            print("Error terminating simulator constellation %s: %s" % (
                                                        self.simulator_name,
                                                        e))
        # terminate baby cloudsim?
        
        # terminate papa cloudsim
        try:
            if self.papa_cloudsim_name:
                print("terminate cloudsim %s" % self.ip)
                cloudsim.terminate(self.papa_cloudsim_name)
                # remove from Redis
                constellation = ConstellationState(self.papa_cloudsim_name)
                constellation.expire(1)
        except Exception, e:
             print("Error terminating papa cloudsim %s" % (
                                                    self.papa_cloudsim_name))

if __name__ == "__main__":
   
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)