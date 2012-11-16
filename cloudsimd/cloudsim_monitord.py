#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import time

import multiprocessing
import redis

import common
from common import MACHINES_DIR
from monitoring import sweep_monitor, latency_sweep
import sys



def log(msg, chan="cloudsim_log"):
    print ("LOG: %s" % msg)
    red = redis.Redis()
    red.publish(chan, msg)

def monitor(root_directory):
    proc = multiprocessing.current_process().name
    log("monitoring '%s' from proc '%s'" % (root_directory, proc))
    
    while True:
        try:
            sweep_monitor(root_directory)
            time.sleep(0.1)
        except Exception, e:
            log("Error %s" % e) 

def monitor_latency(root_directory):
    proc = multiprocessing.current_process().name
    log("monitoring '%s' from proc '%s'" % (root_directory, proc))
    
    while True:
        try:
            latency_sweep(root_directory)
            time.sleep(0.1)
        except Exception, e:
            log("Error %s" % e)
    

def async_monitor(root_directory, proc_count):
    
    procs = []
    log("monitoring machines in '%s'"% (root_directory) )
    try:
        for i in range(proc_count-1):
            p = multiprocessing.Process(target=monitor_latency, args=(root_directory, ) )
            procs.append(p)
        
        p = multiprocessing.Process(target=monitor, args=(root_directory, ) )
        procs.append(p)
        
        for p in procs:
            p.start()
        
        
    except Exception, e:
        log("Error %s" % e)    

if __name__ == "__main__":
    proc_count = 10
    if len(sys.argv) > 1:
        root_directory = sys.argv[1]
    if len(sys.argv) > 2:
        proc_count = int(sys.argv[2])
        
    root_directory =  MACHINES_DIR
    
    try:
        
        log("Cloudsim_monitor daemon started pid %s" % os.getpid())
        async_monitor(root_directory, proc_count)
        
    except Exception, e:
        log("Cloudsim monitor error: %s" %  e)
        
        