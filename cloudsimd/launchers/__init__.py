from __future__ import with_statement
from __future__ import print_function

import imp
import os
import time
import common
from common.machine import MachineDb


directory = os.path.split(__file__)[0]

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

def start_simulator(username, 
                      machine, 
                      package_name, 
                      launch_file_name,
                      launch_args,
                      credentials_ec2, 
                      root_directory):
    #publisher.event({'msg':'About to start simulator'})
    
    machine = matches[0]
   
    script = '". /opt/ros/fuerte/setup.sh; export ROS_IP=%s; export DISPLAY=%s; roslaunch %s %s %s  >/dev/null 2>/dev/null </dev/null &"'%(common.OV_SERVER_IP, common.DISPLAY, package, launchfile, launchargs)
    
    cmd = ['echo', script, '>start_ros.sh']
    cmd_str = ' '.join(cmd)
    
    ret, err = machine.ssh(cmd, args=['-f'])
    # print ("ret: %s<p>err: %s<p>" % (ret, err) )
    
    cmd = ['at', 'NOW', '<start_ros.sh']
    cmd_str = ' '.join(cmd)
    
    
    
def stop_simulator(username, root_directory):
    publisher.event({'msg':'About to stop simulator'})
    mdb = MachineDb(username, machine_dir = root_directory)
    machine = mdb.get_machine(machine_name)
    

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