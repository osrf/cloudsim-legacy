from __future__ import with_statement
from __future__ import print_function

import imp
import os
import time
import common
from common.machine import MachineDb, CONSTELLATION_JSONF_NAME,\
    terminate_constellation
import json
from common.pubsub import RedisPublisher
import traceback

import logging
logging.basicConfig(filename='cloudsimd.log',level=logging.DEBUG)

directory = os.path.split(__file__)[0]



def log(msg, chan = "launchers"):
    try:
        import redis
        r = redis.Redis()
        r.publish(chan, msg)
        logging.info("launchers log: %s" % msg)
    except:
        print("LOG %s" % msg)
    

"""
This module allows to run plugins (each file in the directory except this one)
"""


"""
Load the module from its short name and recover a pointer to the launch function
"""
def load(name):
    path = os.path.join(directory, name + ".py")
    m = imp.load_source(name, path)
    x = getattr(m, "launch")
    return x

"""
Provides a dictionary of modules (one for each type of machine) that returns
"""
def generate_launch_functions():
    launch_functions = {}
    log("generate_launch_functions dir: %s" % directory)
    
    log("LIST %s" % os.listdir(directory) )
    launcher_modules = list(set([x.split(".py")[0] for x in os.listdir(directory)]))
    launcher_modules.remove("__init__")
    
    log("modules: %s" % launcher_modules)
    
    for l in launcher_modules:
        try:
            log("loading launcher %s " % l)
            launch_func = load(l)
            launch_functions[l] = launch_func
        except Exception,e:
            logging.error("launcher load error: %s" % e)
            log("launcher load error '%s'" % e)
            #raise
    return launch_functions

launchers = None

def get_launch_functions():
    global launchers
    
    launchers = generate_launch_functions()
    return launchers
    
def launch(username, 
           config_name, 
           constellation_name, 
           credentials_ec2,
           root_directory):
    
    logging.info("launch %s %s %s" % (username, config_name, constellation_name) )
 
    launchers =  get_launch_functions()
 
    func = launchers[config_name]
 
    domain = username.split('@')[1]
    tags = {}
    # tags['user'] = username
    tags['constellation_name'] = constellation_name
# remove path and .py from the name of this file
    
    
    
    tags['constellation_config'] = config_name
    tags['GMT'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    
    tags['domain'] = domain
 
    domain_dir = os.path.join(root_directory, domain)
 
    constellation_directory = os.path.join(domain_dir, constellation_name)
    # save constellation config in a json file
    os.makedirs(constellation_directory)
    constellation_fname = os.path.join(constellation_directory, CONSTELLATION_JSONF_NAME)
    constellation_info = {}
    constellation_info['name'] = constellation_name
    constellation_info['config'] = config_name
    str = json.dumps(constellation_info)
    with open(constellation_fname,'w') as fp:
        fp.write(str)
    try:
        log("START constellation launch %s [%s]" % (constellation_name, config_name) )
        func(username, constellation_name, tags, credentials_ec2, constellation_directory)
        log("constellation launch %s [%s] DONE" % (constellation_name, config_name) )
    except Exception as e:
        tb = traceback.format_exc()
        logging.error("%s" % tb)
        log("Error during launch: %s" % tb) 

def start_simulator(  username, 
                      constellation_name,
                      machine_name, 
                      package_name, 
                      launch_file_name,
                      launch_args,
                      root_directory):
    
   
    
    log( "start simulator LAUNCHERS. user %s constellation %s machine %s" % (username, constellation_name, machine_name))
    log("    package_name %s, launchfile %s, args %s" %  (package_name,launch_file_name, launch_args ))
    
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(constellation_name, machine_name)
    
    display = ':0'
    server_ip = common.OV_SIM_SERVER_IP
    
    
    #script = '". /opt/ros/fuerte/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s %s  >/dev/null 2>/dev/null </dev/null &"'%(server_ip, display, package_name, launch_file_name, launch_args)
    script = '". /usr/share/drcsim/setup.sh; export ROS_IP=%s; export GAZEBO_IP=%s; export DISPLAY=%s; roslaunch %s %s gzname:=gzserver %s  &"'%(server_ip, server_ip, display, package_name, launch_file_name, launch_args)
    
    cmd = ['echo', script, '>start_ros.sh']
    cmd_str = ' '.join(cmd)
    
    out = machine.ssh_send_command(cmd_str, ['-f'])
    log("%s returned %s" % ( cmd_str, out) )
    
    cmd_str = ". start_ros.sh"
    out = machine.ssh_send_command(cmd_str)
    log("%s returned %s" % ( cmd_str, out) )
    
def stop_simulator(username, constellation_name, machine_name, root_directory):
    log('stop simulator %s' % machine_name)
    
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(constellation_name, machine_name)
    
    cmd_str = 'killall -INT roslaunch'
    out = machine.ssh_send_command(cmd_str)
    log("%s returned %s" % ( cmd_str, out) )
    

def terminate(username, 
              constellation_name, 
              credentials_ec2, 
              root_directory):
    
    log("terminate constellation %s" % constellation_name)
    terminate_constellation(username, constellation_name, credentials_ec2, root_directory)
    
#    mdb = MachineDb(username, machine_dir = root_directory)
#
#    machines = mdb.get_machines_in_constellation(constellation_name)
#    
#    for machine_name, machine  in machines.iteritems():
#        log("  - terminate machine %s" % machine.config.uid)
#        machine.terminate()
    


if __name__ == "__main__":
    x = get_launch_functions()
    print("\nlaunchers:")
    for l in x.keys():
        print ("\t" + l)