from __future__ import with_statement
from __future__ import print_function

import unittest
import os
import redis
from json import dumps

from common import Machine, MachineDb
import commands
import shutil
from common.machine import list_all_machines_accross_domains, get_machine_tag,\
    set_machine_tag, DomainDb


red = redis.Redis()
    
def log(msg):

    red.publish('cloudsim_monitor', msg)

def _create_status(domain, constellation, machine, status_type):
    status = {}
    machine_name = machine.config.uid
    constellation_name = constellation['name']
    status['type'] = status_type
    status['domain'] = domain
    status['constellation_config'] = constellation['config']
    status['constellation_name'] = constellation['name']
    status['machine_name'] = machine_name
    status['launch_state'] = get_machine_tag(domain, constellation_name, machine_name, "launch_state")
    status['up_state'] = get_machine_tag(domain, constellation_name, machine_name, "up")
    return status

def monitor_cloud(domain, constellation, machine):
    constellation_name = constellation['name']
    machine_name = machine.config.uid
    
    log('cloud: %s/%s/%s' % (domain, constellation_name, machine_name) )
    
    status = _create_status(domain, constellation, machine, 'cloud')
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
    if not r:
        set_machine_tag(domain, constellation_name, machine_name, "up", False, 10*60)
    log("monitor cloud  %s %s" % (machine.config.uid, r))
    return r

def monitor_latency(domain, constellation, machine):
    status = _create_status(domain, constellation, machine, 'latency')
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
    status = _create_status(domain, constellation, machine, 'graphics')
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
    
    status = _create_status(domain, constellation, machine, 'simulator')
    x = machine.get_gazebo_status()
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
    log("REMOVE Constellation %s/%s" % (domain, constellation) )
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
        log('sweep: %s/%s/%s [%s]' % (domain, constellation['name'], machine.config.uid, constellation['config']) )
        alive = monitor_cloud( domain, constellation, machine)
        log('   alive %s' % alive)
        if alive:
            x = monitor_xgl(domain, constellation, machine)
            log('   x %s' % x)
            if x:
                s = monitor_simulator(domain, constellation, machine)
                log('   simulation %s' % s)
        else:
            log('   removing %s' % s)
            remove_machine_data(root_directory, domain, constellation, machine)

#def sweep_monitor (root_dir):
#    ddb = DomainDb(root_dir)
#    domains = ddb.get_domains()
#    
#    all_machines = []
#    for domain in domains:
#        email = "user@" + domain
#        mdb = MachineDb(email, root_dir)
#        machines = mdb.get_machines()
#        for constellation_name, constellation in machines.iteritems():
#            for machine_name, machine in constellation['machines'].iteritems():
#                # all_machines.append( (domain, constellation, machine)  )
#                alive = monitor_cloud( domain, constellation, machine)
#                if alive:
#                    x = monitor_xgl(domain, constellation, machine)
#                    if x:
#                        monitor_simulator(domain, constellation, machine)
#                else:
#                    remove_machine_data(root_directory, domain, constellation, machine)



class TestCases(unittest.TestCase):
   
    def test_monitor(self):
        root_directory = "launch_test"
        sweep_monitor(root_directory)

if __name__ == "__main__":
    print("CLOUDSIM_MONITORD tests")
    unittest.main()