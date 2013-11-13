#!/usr/bin/env python
from __future__ import print_function

import os
import sys
import unittest
import time
import datetime
import logging

from cloudsim_rest_api import CloudSimRestApi
import traceback

# add cloudsim directory to sytem path
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)
print (sys.path)

import cloudsimd.launchers.cloudsim as cloudsim
from cloudsimd.launchers.launch_utils.launch_db import ConstellationState
from cloudsimd.launchers.launch_utils.launch_db import get_unique_short_name
from cloudsimd.launchers.launch_utils.testing import get_test_runner
from cloudsimd.launchers.launch_utils.testing import get_boto_path
from cloudsimd.launchers.launch_utils.testing import get_test_path


CLOUDSIM_CONFIG = "CloudSim-stable"
SIM_CONFIG = "Simulator-stable"

try:
    logging.basicConfig(filename='/tmp/rest_integration_test.log',
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                level=logging.DEBUG)
except Exception, e:
    print("Can't enable logging: %s" % e)


def create_task_dict(title, launch_file='vrc_task_1.launch'):
    """
    Generates a simple task for testing purposes
    """
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
    task_dict = {}
    task_dict['task_title'] = title
    task_dict['ros_package'] = 'atlas_utils'
    task_dict['ros_launch'] = launch_file
    task_dict['launch_args'] = ''
    task_dict['timeout'] = '3600'
    task_dict['latency'] = '0'
    task_dict['uplink_data_cap'] = '0'
    task_dict['downlink_data_cap'] = '0'
    task_dict['local_start'] = _get_now_str(-1)  # yesterday
    task_dict['local_stop'] = _get_now_str(1)    # tomorrow
    task_dict['vrc_id'] = 1
    task_dict['vrc_num'] = 1
    return task_dict
    
    
class RestException(Exception):
    pass

def _diff_list(a, b):
    """
    Compares 2 lists and returns the elements in list a only  
    """
    b = set(b)
    return [aa for aa in a if aa not in b]


def launch_constellation(api, config, max_count=100):
    """
    Launch a new constellation, waits for it to appear, and
    returns the new constellation name
    """

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
        
        new_constellations = _diff_list(current_names, previous_constellations)
        print ("%s/%s) new constellations: %s" % (count,
                                                  max_count,
                                                  new_constellations))
        if len(new_constellations) > 0:
             found = True
             constellation_name = new_constellations[0]
    return constellation_name


def terminate_constellation(api,
                            constellation_name,
                            sleep_secs=2,
                            max_count=100):
    """
    Terminates a constellation and waits until the process is done.
    """
    def exists(api, constellation_name):
        constellation_list = api.get_constellations()
        current_names = [x['constellation_name'] \
                               for x in constellation_list]
        return constellation_name in current_names

    constellation_exists = exists(api, constellation_name)
    if not constellation_exists:
        raise RestException("terminate_constellation: "
                        "Constellation '%s' not found" % constellation_name)

    # send the termination signal
    api.terminate_constellation(constellation_name)

    count = 0
    while constellation_exists:
        time.sleep(sleep_secs)
        count += 1
        if count > max_count:
            raise RestException("Timeout in terminate_constellation %s" % (
                                                          constellation_name))
        constellation_exists = exists(api, constellation_name)
        print("%s/%s %s exists: %s" % (count,
                                       max_count, 
                                       constellation_name,
                                       constellation_exists))


def wait_for_constellation_state(api,
                                 constellation_name,
                                 key="constellation_state",
                                 value="running",
                                 max_count=100,
                                 sleep_secs=5):
    """
    Polls constellation state key until its value matches value. This is used
    to wait until a constellation is ready to run simulations 
    """
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
    
    delta_tasks = _diff_list(new_tasks, previous_tasks)
    new_task_id = delta_tasks[0]
    return new_task_id


def wait_for_task_state(cloudsim_api,
                        constellation_name,
                        task_id,
                        target_state,
                        max_count=100,
                        sleep_secs=1):
    """
    Wait until the task is in a target state (ex "running", or "stopped")
    """
    count = 0
    while True:
        time.sleep(sleep_secs)
        count += 1
        if count > max_count:
            raise RestException("Timeout in start_task"
                                "%s for %s" % (task_id, constellation_name))    
        task_dict = cloudsim_api.read_task(constellation_name, task_id)
        current_state = task_dict['task_state']
        print("%s/%s Task %s: %s" % (count, max_count,
                                     task_id,
                                     current_state))
        if current_state == target_state:
            return


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
        raise RestException("Can't start task in state '%s'" % state)

    # run task
    cloudsim_api.start_task(constellation_name, task_id)
    wait_for_task_state(cloudsim_api,
                        constellation_name,
                        task_id,
                        'running',
                        max_count,
                        sleep_secs)


def stop_task(cloudsim_api, constellation_name, task_id, max_count=100,
              sleep_secs=1):
    """
    Stops a task and waits for its status to be "running"
    """
    # check task
    task_dict = cloudsim_api.read_task(constellation_name, task_id)
    state = task_dict['task_state']
    if state != "running":
        raise RestException("Can't stop task in state '%s'" % state)
    
    # run task
    cloudsim_api.stop_task(constellation_name)
    wait_for_task_state(cloudsim_api,
                        constellation_name,
                        task_id,
                        'stopped',
                        max_count,
                        sleep_secs)    

def flush():
    """
    Fake method to avoid crashes, because flush is not present on Delegate_io
    class used by XMLTestRunner.
    """
    pass


class RestTest(unittest.TestCase):
    """
    Test that Creates a CloudSim on AWS. A simulator is then launched
    from that CloudSim and a simulation task is run.
    This test is run by Jenkins when CloudSim code is modified.
    """
    def title(self, text):
        print("")
        print("#######################################")
        print("#")
        print("# %s" % text)
        print("#")
        print("#######################################")
        

    def setUp(self):
            
        self.title("setUp")
        # provide no op flush to avoid crashes
        sys.stdout.flush = flush
        sys.stderr.flush = flush
        
        self.cloudsim_api = None
        self.simulator_name = None
        self.papa_cloudsim_name = None
        self.baby_cloudsim_name = None
        
        self.user = 'admin'
        self.password = 'test123'
        
        self.papa_cloudsim_name = get_unique_short_name('rst')
        self.data_dir = get_test_path("rest_test")
        self.creds_fname = get_boto_path()
        self.ip = None
        
        print("data dir: %s" % self.data_dir)
        print("cloudsim constellation: %s" % self.papa_cloudsim_name)
        print("user: %s, password: %s" % (self.user, self.password))

    def test(self):
        self.title("create_cloudsim")
        self.ip = cloudsim.create_cloudsim(username=self.user,
                                  credentials_fname=self.creds_fname,
                                  configuration=CLOUDSIM_CONFIG,
                                  authentication_type="Basic",
                                  password=self.password,
                                  data_dir=self.data_dir,
                                  constellation_name=self.papa_cloudsim_name)
        self.assertTrue(True, "cloudsim not created")
        print("papa cloudsim %s created in %s" % (self.ip, self.data_dir))
        print("\n\n")
        print('api = CloudSimRestApi("%s", "%s", "%s")' % (self.ip,
                                                     self.user,
                                                     self.password))
        self.cloudsim_api = CloudSimRestApi(self.ip, self.user, self.password)
        
        self.title("launch baby cloudsim")
        self.baby_cloudsim_name = launch_constellation(self.cloudsim_api, 
                                                   config=CLOUDSIM_CONFIG)
        print("# baby cloudsim %s launched" % (self.baby_cloudsim_name))
        self.assertTrue(True, "baby cloudsim not created")

        self.title("Wait for baby cloudsim readyness")
        print("api.get_constellation_data('%s')" % self.baby_cloudsim_name)
        wait_for_constellation_state(self.cloudsim_api,
                                     self.baby_cloudsim_name,
                                     key="constellation_state",
                                     value="running",
                                     max_count=100)
        self.assertTrue(True, "baby cloudsim not ready")
        print("# baby cloudsim machine ready")

        self.title("Update baby cloudsim")
        self.cloudsim_api.update_constellation(self.baby_cloudsim_name)
        wait_for_constellation_state(self.cloudsim_api,
                                     self.baby_cloudsim_name,
                                     key="constellation_state",
                                     value="running",
                                     max_count=100)
        print("# baby cloudsim machine updated")

        self.title("launch simulator")
        self.simulator_name = launch_constellation(self.cloudsim_api, 
                                                   config=SIM_CONFIG)
        print("# Simulator %s launched" % (self.simulator_name))
        self.assertTrue(True, "simulator not created")
 
        self.title("Wait for simulator readyness")
        print("api.get_constellation_data('%s')" % self.simulator_name)
        wait_for_constellation_state(self.cloudsim_api,
                                     self.simulator_name,
                                     key="launch_stage",
                                     value="running",
                                     max_count=100)
        self.assertTrue(True, "simulator not ready")
        print("# Simulator machine ready")
 
        # the simulator is ready!
        self.title("# create task")
        print('tid = create_task(api, "%s", '
              'create_task_dict("test 0"))' % self.simulator_name)
        print("\n\n")
        task_dict = create_task_dict("test task 1")
        print("%s" % task_dict)
        self.task_id = create_task(self.cloudsim_api,
                                   self.simulator_name,
                                   task_dict)
        self.assertTrue(True, "task not created")
        run_task(self.cloudsim_api,self.simulator_name, self.task_id)
        self.assertTrue(True, "task not run")
        self.title("# stop task")
        stop_task(self.cloudsim_api,self.simulator_name, self.task_id)
        self.assertTrue(True, "task not stopped")

    def tearDown(self): 
        self.title("tearDown")
        
        self.title("terminate baby cloudsim")
        try:
            if self.cloudsim_api and self.baby_cloudsim_name:
                terminate_constellation(self.cloudsim_api,
                                        self.baby_cloudsim_name)
            else:
                print("No baby cloudsim created")
        except Exception, e:
            print("Error terminating baby cloudsim constellation %s: %s" % (
                                                    self.baby_cloudsim_name,
                                                    e))

        self.title("terminate simulator")
        try:
            if self.cloudsim_api and self.simulator_name:
                terminate_constellation(self.cloudsim_api, self.simulator_name)
            else:
                print("No simulator created")
        except Exception, e:
            print("Error terminating simulator constellation %s: %s" % (
                                                        self.simulator_name,
                                                        e))
            tb = traceback.format_exc()
            print("traceback:  %s" % tb)

        self.title("terminate papa cloudsim")
        try:
            if self.papa_cloudsim_name and self.ip:
                print("terminate cloudsim '%s' %s" % (self.papa_cloudsim_name,
                                                      self.ip))
            cloudsim.terminate(self.papa_cloudsim_name)
            # remove from Redis
            constellation = ConstellationState(self.papa_cloudsim_name)
            constellation.expire(1)
      
        except Exception, e:
             print("Error terminating papa cloudsim '%s' : %s" % (
                                                    self.papa_cloudsim_name,
                                                    e))
             tb = traceback.format_exc()
             print("traceback:  %s" % tb)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)

