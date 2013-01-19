#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import time

import multiprocessing
import redis

import sys
import json

import traceback
from launchers.launch_utils.launch_db import get_constellation_data

TICK_INTERVAL = 1
MACHINES_DIR = '/var/www-cloudsim-auth/machines'


def log(msg, chan="cloudsim_log"):
    print ("LOG: %s" % msg)
    red = redis.Redis()
    red.publish(chan, msg)

#def monitor(root_directory):
#    proc = multiprocessing.current_process().name
#    log("Sweep monitoring '%s' from proc '%s'" % (root_directory, proc))
#    
#    while True:
#        try:
#            sweep_monitor(root_directory)
#            time.sleep(0.1)
#        except Exception, e:
#            
#            tb = traceback.format_exc()
#            log("Error during sweep monitor: %s" % tb) 

def monitor_latency(root_directory):
    proc = multiprocessing.current_process().name
    log("Latency monitoring '%s' from proc '%s'" % (root_directory, proc))
    
    while True:
        try:
            latency_sweep(root_directory)
            time.sleep(0.1)
        except Exception, e:
            log("Error during latency sweep: %s" % e)
    

def async_monitor(root_directory, proc_count):
    
    procs = []
    log("monitoring machines in '%s'"% (root_directory) )
    try:
        for i in range(proc_count-1):
            p = multiprocessing.Process(target=monitor_latency, args=(root_directory, ) )
            procs.append(p)
        
        p = multiprocessing.Process(target=monitor, args=(root_directory, ) )
        procs.append(p)
        
        p = multiprocessing.Process(target=tick_monitor, args=(TICK_INTERVAL, ) )
        procs.append(p)
        
        for p in procs:
            p.start()
        
        
    except Exception, e:
        log("Error %s" % e)

def tick_monitor(tick_interval):
    count = 0
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    log("monitoring '%s' from proc '%s'" % (root_directory, proc))
    while True:
        count +=1
        time.sleep(tick_interval)
        tick = {}
        tick['count'] = count
        tick['type'] = 'tick'
        tick['interval'] = tick_interval
        msg = json.dumps(tick)
        red.publish("cloudsim_tick", msg)
    

def monitor(root_directory):
    
    while True:
        
        print(root_directory)
        for domain_name in os.listdir(root_directory):
                if domain_name != "rip":
                    domain_path = os.path.join(root_directory, domain_name )
                    for constellation_name in os.listdir(domain_path):
                        constellation = get_constellation_data(domain_name, constellation_name)
                        print ("\n\n========\n%s/%s\n%s" % (domain_name, constellation_name,constellation ))
                       
                
        time.sleep(1)

if __name__ == "__main__":
    proc_count = 3
    if len(sys.argv) > 1:
        root_directory = sys.argv[1]
    if len(sys.argv) > 2:
        proc_count = int(sys.argv[2])
        
    root_directory =  MACHINES_DIR
    
    try:
        log("Cloudsim_monitor daemon started pid %s" % os.getpid())

        monitor(root_directory)
        
    except Exception, e:
        log("Cloudsim monitor error: %s" %  e)
        
        