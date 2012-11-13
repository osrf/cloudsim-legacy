from __future__ import with_statement
from __future__ import print_function

import unittest
import os
import redis
from json import dumps

from common import Machine2
import commands
import shutil



def monitor_cloud(red, domain, machine):
    status = {}
    status['machine'] = machine.config.uid
    status['type'] = 'test'
    
    cloud = machine.get_aws_status()
    aws_status = {}
    
    aws_status.update(status)
    aws_status['success'] = cloud['status']
    aws_status.update(cloud)
    aws_status['status'] = "cloud"

    str = dumps(aws_status)
    red.publish(domain, str)
    r = True
    if cloud['status'] == "terminated":
        r = False
    if cloud['status'] == "does_not_exist":
        r = False

    return r

    
def monitor_latency(red, domain, machine):
    status = {}
    status['machine'] = machine.config.uid
    status['type'] = 'test'

    ping_status = {}
    ping_status['status'] = "latency"
    ping_status.update(status)
    ping_result = machine.ping()
    if ping_result:
        ping_status.update(ping_result)
    else:
        ping_status['fail'] = "host unreacheable" 
    str = dumps(ping_status)
    red.publish(domain, str)

def monitor_xgl(red, domain, machine):
    x = machine.get_X_status()
    
    status = {}
    status['machine'] = machine.config.uid
    status['type'] = 'test'

    x_status = {}
    x_status.update(status)
    x_status['status'] = "graphics"
    x_status['success'] = x
    str = dumps(x_status)
    red.publish(domain, str)
    return x

def monitor_simulator(red, domain, machine):
    x = machine.get_gazebo_status()
    
    status = {}
    status['machine'] = machine.config.uid
    status['type'] = 'test'
        
    g_status = {}
    g_status.update(status)
    g_status['status'] = "simulator"
    g_status['success'] = x
    str = dumps(g_status)
    red.publish(domain, str)
    return x




def get_machine_instance_paths_and_domains(root_directory):
    ret =[]
    domains = os.listdir(root_directory)
    for domain in domains:
        path = os.path.join(root_directory,domain)
        machines = os.listdir(path)
        for machine_name in machines:
            machine_fname = os.path.join(path, machine_name, "instance.json")
            if os.path.exists(machine_fname):
                ret.append( (machine_fname, domain) )
    return ret

def remove_machine_data(root_directory, machine_data_fname):
    machine_data_dir = os.path.split(machine_data_fname)[0]
    rip_dir = os.path.join( root_directory,"..",  "rip") 
    if not os.path.exists(rip_dir):
        os.makedirs(rip_dir)    
    shutil.move(machine_data_dir, rip_dir)
        
def latency_sweep(root_directory):
    red = redis.Redis()
    for machine_data_fname, domain in get_machine_instance_paths_and_domains(root_directory):
        machine = Machine2.from_file(machine_data_fname)
        monitor_latency(red, domain, machine)
        

def sweep_monitor (root_directory):
    red = redis.Redis()
    for machine_data_fname, domain in get_machine_instance_paths_and_domains(root_directory):
        machine = Machine2.from_file(machine_data_fname)
        alive = monitor_cloud(red, domain, machine)
        if alive:
            #monitor_latency(red, domain, machine)
            x = monitor_xgl(red, domain, machine)
            if x:
                monitor_simulator(red, domain, machine)
        else:
            remove_machine_data(root_directory, machine_data_fname)


class TestCases(unittest.TestCase):
    
    def test_paths(self):
        root_directory = "launch_test"
        for machine_data, domain in get_machine_instance_paths_and_domains(root_directory):
            self.assert_(os.path.exists(machine_data), '%s not a real instance data file' % machine_data)
            print(domain, ": machine: ", machine_data)
    
    def test_monitor(self):
        root_directory = "launch_test"
        sweep_monitor(root_directory)

if __name__ == "__main__":
    print("CLOUDSIM_MONITORD tests")
    unittest.main()