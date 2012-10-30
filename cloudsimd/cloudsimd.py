#!/usr/bin/python

import os
import time

import multiprocessing
from json import loads
import redis

import common
from common import RedisPublisher
import uuid

redis_client = redis.Redis()

# register the daemon
# sudo initctl reload-configuration

# How to start and stop
# sudo start script


jobs = []

def launch(config_name, username):
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    red.publish("cloudsim_log", "Launching '%s' for '%s' from '%s'" % (config_name, username, proc))
   
    #red.publish("cloudsim_log", "X")
    cdb = common.ConfigsDb(username)
    #red.publish("cloudsim_log", "X")
    
    config = cdb.get_configs()[config_name]
    
    Machine2.from_file()
    
    publisher = RedisPublisher(username)
    machine_name = uuid.uuid1()
    
    tags = {'configuration':config_name , 'user':username}
               
    machine = Machine2(machine_name,
                         config,
                         publisher.event,
                         tags)
    
    machine.create_ssh_connect_script()
    
    print("Waiting for ssh")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    print("Waiting for setup to complete")
    machine.ssh_wait_for_ready()
    
#    repeats = 3
#    for i in range(repeats):
#        print("Checking status [%s / %s]" % (i+1, repeats))
#        
#        m =  machine.test_aws_status()
#        print("    aws status= %s" % m)
#        try:
#            p = machine.ping()
#            print("    ping= %s" % str(p) )
#        except Exception, e:
#            print("    ",e)
#        x = machine.test_X()
#        print("    X= %s" % x)
#        g = machine.test_gazebo()
#        print("    gazebo= %s" % g)
#          
#    print("Shuting down\n\n\n")      
#    machine.terminate()
#    print("\n\n\n")
#    sys.stdout.flush()

    
    # cdb = common.ConfigDb(username)
    return
    
    
def async_launch(config, username):
    redis_client.publish("cloudsim_log", "launch! %s for %s"% (config, username) )
    
    try:
        p = multiprocessing.Process(target=launch, args=(config, username))
        # jobs.append(p)
        p.start()
    except Exception, e:
        redis_client.publish("cloudsim_log",e)



def run():
    redis_client.publish("cloudsim_log", 
                         "Cloudsim daemon started pid %s" %  os.getpid())

    ps = redis_client.pubsub()
    ps.subscribe("cloudsim_cmds")
    
    for msg in ps.listen():
        redis_client.publish("cloudsim_log", "CLOUDSIM = '%s'" % msg) 
        try:
            data = loads(msg['data'])
            cmd = data['command']
            username = data['username']
            # redis_client.publish("cloudsim_log" , "[%s] : %s" % (cmd, msg) )
            if cmd == 'launch':
                config = data['configuration']
                async_launch(config, username)
        except:
            redis_client.publish("cloudsim_log", "not a valid message [%s]" % msg)

run()