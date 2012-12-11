#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import time

import multiprocessing
from json import loads


import common
from common import RedisPublisher
import uuid
import launchers
from common import MACHINES_DIR
from common import BOTO_CONFIG_FILE_USEAST
from common import Machine

import redis
from common.machine import get_unique_short_name
# register the daemon
# sudo initctl reload-configuration

# How to start and stop
# sudo start script

# jobs = []

def log(msg, chan="cloudsim_log"):
    try:
        
        print ("LOG: %s" % msg)
        red = redis.Redis()
        red.publish(chan, msg)
    except Exception, e:
        print("cloudsimd> %s" % msg)

def launch( username, config_name, credentials_ec2 =  BOTO_CONFIG_FILE_USEAST, 
            root_directory =  MACHINES_DIR):
    
    red = redis.Redis()
    constellation_name =  "c" + get_unique_short_name()
    
    
    try:
        proc = multiprocessing.current_process().name
        #log("cloudsimd.py launch")
        log("Launching constellation %s, config '%s' for user '%s' from proc '%s'" % (constellation_name, config_name,  username, proc))
        publisher = RedisPublisher(username) 
        launchers.launch(username, 
                         config_name, 
                         constellation_name, 
                         publisher,
                         credentials_ec2,
                         root_directory)
    except Exception, e:
        log("cloudsimd.py launch error: %s" % e)
    return
    
"""
Terminates the machine via the cloud interface. Files will be removed by the 
monitoring process
"""
def terminate(username, 
              constellation, 
              credentials_ec2,
              root_directory):
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    log("terminate '%s' for '%s' from proc '%s'" % (constellation, username, proc))

    try:
        publisher = RedisPublisher(username) 
        launchers.terminate(username, constellation, publisher, credentials_ec2,
                            root_directory)
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)
    

    
def async_launch(username, config):
    log("cloudsimd async_launch [config %s for user %s]"% (config, username) )
    try:
        p = multiprocessing.Process(target=launch, args=(username, config, ))
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("cloudsimd async_launch Error %s" % e)

def async_terminate(username, constellation):
    log("terminate! %s for %s"% (constellation, username) )
    credentials_ec2 =  BOTO_CONFIG_FILE_USEAST
    root_directory =  MACHINES_DIR
    try:
        
        p = multiprocessing.Process(target=terminate, args= (username, constellation, credentials_ec2, root_directory,)  )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)

def start_simulator(username, constellation, machine_name, package_name, launch_file_name,launch_args):

    try:
#        log("START_SIMU user %s", username )
#        log("START_SIMU on machine %s", machine_name )
        root_directory =  MACHINES_DIR
        
        launchers.start_simulator(username,
                                  constellation, 
                              machine_name, 
                              package_name, 
                              launch_file_name,
                              launch_args,
                              root_directory)

    except Exception, e:
        log("start_simulator error: %s" % e )
                
def async_start_simulator(username, constellation, machine, package_name, launch_file_name,launch_args ):
    log("async start simulator! user %s machine %s, pack %s launch %s args '%s'" % (username, machine, package_name, 
                                                                                    launch_file_name, launch_args ))
    try:
        p = multiprocessing.Process(target=start_simulator, args=(username, constellation, machine, package_name, launch_file_name,launch_args ) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)

def stop_simulator(username, constellation,  machine):
    try:
        root_directory =  MACHINES_DIR
        launchers.stop_simulator(username, constellation, machine, root_directory)
    except Exception, e:
        log("stop_simulator error: %s" % e )
        
def async_stop_simulator(username, constellation, machine):
    log("async stop simulator! user %s machine %s" % (username, machine))
    try:
        p = multiprocessing.Process(target=stop_simulator, args=(username, constellation,  machine) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)
    
    

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
                constellation = data['constellation']
                async_terminate(username, constellation)
            
            if cmd == "start_simulator" :
                machine = data['machine']
                constellation = data['constellation']
                package_name = data['package_name']
                launch_file_name = data['launch_file_name'] 
                launch_args = data['launch_args']
                async_start_simulator(username, constellation, machine, package_name, launch_file_name,launch_args ) 
            
            if cmd == "stop_simulator" :
                machine = data['machine']
                constellation = data['constellation']
                async_stop_simulator(username, constellation, machine)
                
        except:
            log("not a valid message [%s]" % msg)
            

if __name__ == "__main__":
    
    try:
        
        log("Cloudsim daemon started pid %s" %  os.getpid())
        run()
        
    except Exception, e:
        log("Cloudsim daemon error: %s" %  e)