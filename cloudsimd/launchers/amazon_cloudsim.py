from __future__ import print_function

import unittest
import time

import boto
from boto.pyami.config import Config as BotoConfig

#from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data

from launch_utils.testing import get_test_runner
from launch_utils.launch_db import log_msg
# from launch_utils.monitoring import constellation_is_terminated,\
#     update_machine_aws_states, get_ssh_client, monitor_cloudsim_ping,\
#     monitor_launch_state



def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


# def monitor(constellation_name, counter):
#     time.sleep(1)
#     if constellation_is_terminated(constellation_name):
#         return True
#
#     constellation = ConstellationState(constellation_name)
#
#     simulation_state = constellation.get_value('simulation_state')
#     update_machine_aws_states(constellation_name, {'simulation_aws_id':"simulation_aws_state"}) 
#
#     ssh_sim = get_ssh_client(constellation_name, simulation_state,'simulation_ip', 'sim_key_pair_name' )
#
#     monitor_cloudsim_ping(constellation_name, 'simulation_ip', 'simulation_latency')
#     monitor_launch_state(constellation_name, ssh_sim, simulation_state, "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg')
#     return False #log("monitor not done")    




class DbCase(unittest.TestCase):

    def test_set_get(self):
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data(constellation, value, expiration)
        data = get_constellation_data(constellation)
        self.assert_(data['a'] == value['a'], "redis db value not set")

if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       
