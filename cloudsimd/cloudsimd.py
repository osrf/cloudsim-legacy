#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import time

import multiprocessing
from json import loads
import redis

import common
from common import RedisPublisher
import uuid
import launchers
from common import MACHINES_DIR
from common import BOTO_CONFIG_FILE_USEAST
from common import Machine


# register the daemon
# sudo initctl reload-configuration

# How to start and stop
# sudo start script

# jobs = []

def log(msg, chan="cloudsim_log"):
    print ("LOG: %s" % msg)
    red = redis.Redis()
    red.publish(chan, msg)

def launch( username, config_name, credentials_ec2 =  BOTO_CONFIG_FILE_USEAST, 
            root_directory =  MACHINES_DIR):
    
    red = redis.Redis()
    machine_name = str(uuid.uuid1())
    try:
        proc = multiprocessing.current_process().name
        
         
        log("Launching machine %s, config '%s' for user '%s' from proc '%s'" % (machine_name, config_name,  username, proc))

        publisher = RedisPublisher(username) 
        launchers.launch(username, 
                         config_name, 
                         machine_name, 
                         publisher,
                         credentials_ec2,
                         root_directory)
        
    except Exception, e:
        red.publish("cloudsim_log", e)
    
    return
    
"""
Terminates the machine via the cloud interface. Files will be removed by the 
monitoring process
"""
def terminate(username, 
              machine_name, 
              credentials_ec2,
              root_directory):
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    log("terminate '%s' for '%s' from proc '%s'" % (machine_name, username, proc))

    try:
        publisher = RedisPublisher(username) 
        launchers.terminate(username, machine_name, publisher, credentials_ec2,
                            root_directory)
    except Exception, e:
        red.publish("cloudsim_log", e)
    

    
def async_launch(username, config):
    log("launch! %s for %s"% (config, username) )
    
    try:
        p = multiprocessing.Process(target=launch, args=(username, config, ))
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)

def async_terminate(username, machine):
    log("terminate! %s for %s"% (machine, username) )
    credentials_ec2 =  BOTO_CONFIG_FILE_USEAST
    root_directory =  MACHINES_DIR
    try:
        
        p = multiprocessing.Process(target=terminate, args= (username, machine, credentials_ec2, root_directory,)  )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)

def start_simulator(username, machine_name, package_name, launch_file_name,launch_args):

    try:
#        log("START_SIMU user %s", username )
#        log("START_SIMU on machine %s", machine_name )
        root_directory =  MACHINES_DIR
        
        launchers.start_simulator(username, 
                              machine_name, 
                              package_name, 
                              launch_file_name,
                              launch_args,
                              root_directory)

    except Exception, e:
        log("start_simulator error: %s" % e )
                
def async_start_simulator(username, machine, package_name, launch_file_name,launch_args ):
    log("async start simulator! user %s machine %s, pack %s launch %s args '%s'" % (username, machine, package_name, 
                                                                                    launch_file_name, launch_args ))
    try:
        p = multiprocessing.Process(target=start_simulator, args=(username, machine, package_name, launch_file_name,launch_args ) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)

def stop_simulator(username, machine):
    try:
        root_directory =  MACHINES_DIR
        launchers.stop_simulator(username, machine, root_directory)
    except Exception, e:
        log("stop_simulator error: %s" % e )
        
def async_stop_simulator(username, machine):
    log("async stop simulator! user %s machine %s" % (username, machine))
    try:
        p = multiprocessing.Process(target=stop_simulator, args=(username, machine) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)
    
    

def run():
    
    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")
    
    
    log("CLOUDSIMD STARTED")
    for msg in ps.listen():
        log("CLOUDSIMD EVENT") 
        try:
            data = loads(msg['data'])
            cmd = data['command']
            username = data['username']
            log("             CMD= \"%s\"" % cmd)
            # redis_client.publish("cloudsim_log" , "[%s] : %s" % (cmd, msg) )
            if cmd == 'launch':
                config = data['configuration']
                # log("CLOUDSIM Launch %s" % config)
                async_launch(username, config)
            
            if cmd == 'terminate':
                machine = data['machine']
                async_terminate(username, machine)
            
            if cmd == "start_simulator" :
                machine = data['machine']
                package_name = data['package_name']
                launch_file_name = data['launch_file_name'] 
                launch_args = data['launch_args']
                async_start_simulator(username, machine, package_name, launch_file_name,launch_args ) 
            
            if cmd == "stop_simulator" :
                machine = data['machine']
                async_stop_simulator(username, machine)
                
        except:
            log("not a valid message [%s]" % msg)
            

if __name__ == "__main__":
    
    try:
        
        log("Cloudsim daemon started pid %s" %  os.getpid())
        run()
        
    except Exception, e:
        log("Cloudsim daemon error: %s" %  e)