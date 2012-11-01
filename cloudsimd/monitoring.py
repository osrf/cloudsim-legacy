from __future__ import with_statement
from __future__ import print_function

import unittest
import os
import redis
from json import dumps

from common import Machine2

def monitor_machine(domain, machine):
    
    status = {}
    status['machine'] = machine.config.uid
    
    red = redis.Redis()
    
    
    #print("Monitor machine.. domain  %s, machine %s" % (domain, machine.config.uid))
    #print("  Machine %s" % machine)
    aws_status = {}
    aws_status['status'] = "cloud"
    aws_status['machine'] = machine.config.uid
    aws_status.update(status)
    
    str = dumps(aws_status)
    red.publish(domain, str)
    
    
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
    
    x_status = {}
    x_status.update(status)
    x_status['status'] = "graphics"
    x_status['success'] = machine.get_X_status()
    str = dumps(x_status)
    red.publish(domain, str)
   # print("    X= %s" % x)
    g_status = {}
    g_status.update(status)
    g_status['status'] = "simulator"
    g_status['success'] = machine.get_gazebo_status()
    str = dumps(g_status)
    red.publish(domain, str)
    
    #print("    gazebo= %s" % g)
            

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
        
def sweep_monitor (root_directory):
    
    for machine_data, domain in get_machine_instance_paths_and_domains(root_directory):
        machine = Machine2.from_file(machine_data)
        monitor_machine(domain, machine)


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
    print("CLOUDSIMD tests")
    unittest.main()