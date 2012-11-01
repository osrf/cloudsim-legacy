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
from common import Machine2
from monitoring import sweep_monitor


# register the daemon
# sudo initctl reload-configuration

# How to start and stop
# sudo start script

# jobs = []

def log(msg):
    print ("LOG: %s" % msg)
    red = redis.Redis()
    red.publish("cloudsim_log", msg)

def launch(config_name, username, credentials_ec2 =  BOTO_CONFIG_FILE_USEAST, root_directory =  MACHINES_DIR):
    
    
    try:
        red = redis.Redis()
        proc = multiprocessing.current_process().name
        log("Launching '%s' for '%s' from proc '%s'" % (config_name, username, proc))
        
        machine_name = str(uuid.uuid1()) 
        publisher = RedisPublisher(username) 
        
                
        launchers.launch(config_name, 
                         username, 
                         machine_name, 
                         publisher,
                         credentials_ec2,
                         root_directory)
        
    except Exception, e:
        red.publish("cloudsim_log", e)
    
    return
    

def monitor(root_directory):
    proc = multiprocessing.current_process().name
    log("monitoring '%s' from proc '%s'" % (root_directory, proc))
    
    while True:
        try:
            sweep_monitor(root_directory)
        except Exception, e:
            log("Error %s" % e) 
    
    
def async_launch(config, username):
    log("launch! %s for %s"% (config, username) )
    
    try:
        p = multiprocessing.Process(target=launch, args=(config, username))
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)

def async_monitor():
    
    root_directory =  MACHINES_DIR
    log("monitoring machines in '%s'"% (root_directory) )
    
    try:
        p = multiprocessing.Process(target=monitor, args=(root_directory, ) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)    
    

def run():
    
    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")
    
     
    async_monitor()
    
    for msg in ps.listen():
        log("COMMAND = '%s'" % msg) 
        try:
            data = loads(msg['data'])
            cmd = data['command']
            username = data['username']
            # redis_client.publish("cloudsim_log" , "[%s] : %s" % (cmd, msg) )
            if cmd == 'launch':
                config = data['configuration']
                async_launch(config, username)
        except:
            log("not a valid message [%s]" % msg)
            
            

if __name__ == "__main__":
    
    try:
        
        log("Cloudsim daemon started pid %s" %  os.getpid())
        run()
        
    except Exception, e:
        log("Cloudsim daemon error: %s" %  e)