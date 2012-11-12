from __future__ import with_statement
from __future__ import print_function

import imp
import os
import time
import common
from common.machine import MachineDb


directory = os.path.split(__file__)[0]


def log(msg, chan = "launchers"):
    import redis
    r = redis.Redis()
    r.publish(chan, msg)
    

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
def get_launch_functions():
    launch_functions = {}
    print("dir:", directory)
    print(os.listdir(directory) )
    launcher_modules = list(set([x.split(".py")[0] for x in os.listdir(directory)]))
    launcher_modules.remove("__init__")
    
    print(launcher_modules)
    
    for l in launcher_modules:
        try:
            launch_func = load(l)
            launch_functions[l] = launch_func
        except Exception,e:
            print(e)
    return launch_functions

launchers = None

def launch(username, 
           config_name, 
           machine_name, 
           publisher,
           credentials_ec2,
           root_directory):
    
    global launchers
    
    if not launchers:
        launchers =  get_launch_functions()
    
    func = launchers[config_name]
    
    tags = {}
    tags['user'] = username
    tags['machine'] = machine_name
# remove path and .py from the name of this file
    tags['configuration'] = config_name
    tags['GMT'] = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    
    domain = username.split('@')[1]
    userdir = os.path.join(root_directory, domain)
        
    func(username, machine_name, tags, publisher, credentials_ec2, userdir)

def start_simulator(  username, 
                      machine_name, 
                      package_name, 
                      launch_file_name,
                      launch_args,
                      root_directory):
    
   
    
    log( "start simulator LAUNCHERS. user %s machine %s" % (username, machine_name))
    log("    package_name %s, launchfile %s, args %s" %  (package_name,launch_file_name, launch_args ))
    
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(machine_name)
    
    display = common.DISPLAY
    server_ip = common.OV_SERVER_IP
    
    
    #script = '". /opt/ros/fuerte/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s %s  >/dev/null 2>/dev/null </dev/null &"'%(server_ip, display, package_name, launch_file_name, launch_args)
    script = '". /usr/share/drcsim-1.0/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s gzname:=gzserver %s  &"'%(server_ip, display, package_name, launch_file_name, launch_args)
    
    cmd = ['echo', script, '>start_ros.sh']
    cmd_str = ' '.join(cmd)
    
    out = machine.ssh_send_command(cmd_str, ['-f'])
    log("%s returned %s" % ( cmd_str, out) )
    
    cmd_str = ". start_ros.sh"
    out = machine.ssh_send_command(cmd_str)
    log("%s returned %s" % ( cmd_str, out) )
    
def stop_simulator(username, machine_name, root_directory):
    log('stop simulator %s' % machine_name)
    
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(machine_name)
    
    cmd_str = 'killall -INT roslaunch'
    out = machine.ssh_send_command(cmd_str)
    log("%s returned %s" % ( cmd_str, out) )
    

def terminate(username, 
              machine_name, 
              publisher, 
              credentials_ec2, 
              root_directory):
    
    publisher.event({'msg':'About to terminate'})
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(machine_name)
    machine.terminate()
    



if __name__ == "__main__":
    x = get_launch_functions()
    print (x)