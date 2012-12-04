from __future__ import with_statement
from __future__ import print_function

import unittest
import os
import redis
from json import dumps

from common import Machine, MachineDb
import commands
import shutil
from common.machine import list_all_machines_accross_domains

red = redis.Redis()

def log(msg):
    red.publish('cloudsim_monitor', msg)

def monitor_cloud(domain, constellation, machine):
    log('cloud: %s/%s/%s' % (domain, constellation['name'], machine.config.uid) )
    status = {}
    status['machine'] = machine.config.uid
    status['constellation_name'] = constellation['name']
    status['constellation_config'] = constellation['config']
    status['type'] = 'cloud'
    
    cloud = machine.get_aws_status()
    aws_status = {}
    aws_status.update(status)
    aws_status.update(cloud)
    
    str = dumps(aws_status)
    red.publish(domain, str)
    r = True
    if cloud['state'] == "terminated":
        r = False
    if cloud['state'] == "does_not_exist":
        r = False

    return r

    
def monitor_latency(domain, constellation, machine):
    status = {}
    status['machine_name'] = machine.config.uid
    status['constellation_name'] = constellation['name']
    status['constellation_config'] = constellation['config']
    status['domain'] = domain
    status['type'] = 'latency'

    ping_status = {}
    
    ping_status.update(status)
    ping_result = machine.ping()
    if ping_result:
        ping_status.update(ping_result)
        ping_status['result'] ='success'
    else:
        ping_status['result'] ='failure'

    str = dumps(ping_status)
    red.publish(domain, str)
    return ping_status['result'] =='success'

def monitor_xgl(domain, constellation, machine):
    x = machine.get_X_status()
    
    status = {}
    status['machine_name'] = machine.config.uid
    status['constellation_name'] = constellation['name']
    status['constellation_config'] = constellation['config']
    status['type'] = 'graphics'
    x_status = {}
    x_status.update(status)
    if x:
        x_status['result'] = 'success'
    else:
        x_status['result'] = 'failure'
    str = dumps(x_status)
    red.publish(domain, str)
    return x

def monitor_simulator(domain, constellation, machine):
    x = machine.get_gazebo_status()
    
    status = {}
    status['machine_name'] = machine.config.uid
    status['constellation_name'] = constellation['name']
    status['constellation_config'] = constellation['config']
    status['type'] = 'simulator'
        
    g_status = {}
    g_status.update(status)

    if x:
        g_status['result'] = 'success'
    else:
        g_status['result'] = 'failure'
    str = dumps(g_status)
    red.publish(domain, str)
    return x

def remove_constellation(root_directory, domain, constellation):
    constellation_fname = os.path.join(root_directory, domain, constellation)
    rip_dir = os.path.join( root_directory,"..",  "rip") 
    if not os.path.exists(rip_dir):
        os.makedirs(rip_dir)    
    shutil.move(constellation_fname, rip_dir)

def remove_machine_data(root_directory, domain, constellation, machine):
    log("Removing machine %s/%s/%s/%s" % (root_directory, domain, constellation, machine))
    machine_data_fname = machine.config.instance_fname
    machine_data_dir = os.path.split(machine_data_fname)[0]
    rip_dir = os.path.join( root_directory,"..",  "rip") 
    if not os.path.exists(rip_dir):
        os.makedirs(rip_dir)    
    shutil.move(machine_data_dir, rip_dir)
    
def latency_sweep(root_directory):
    for domain, constellation, machine in list_all_machines_accross_domains(root_directory):
        monitor_latency( domain, constellation, machine)

def sweep_monitor (root_directory):
    log('sweep "%s"' % root_directory)
    for domain, constellation, machine in list_all_machines_accross_domains(root_directory):
        #log('sweep: %s/%s/%s' % (domain, constellation, machine.config.uid) )
        alive = monitor_cloud( domain, constellation, machine)
        if alive:
            x = monitor_xgl(domain, constellation, machine)
            if x:
                monitor_simulator(domain, constellation, machine)
        else:
            remove_machine_data(root_directory, domain, constellation, machine)

class TestCases(unittest.TestCase):
    
    #def test_paths(self):
    #   root_directory = "launch_test"
        #for machine_data, constellation, domain in list_all_machines_accross_domains(root_directory):
        #    self.assert_(os.path.exists(machine_data), '%s not a real instance data file' % machine_data)
        #    print(domain, ": machine: ", machine_data)
    
    def test_monitor(self):
        root_directory = "launch_test"
        sweep_monitor(root_directory)

if __name__ == "__main__":
    print("CLOUDSIM_MONITORD tests")
    unittest.main()