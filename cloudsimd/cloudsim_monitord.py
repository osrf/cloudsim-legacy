#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import time

import multiprocessing
import redis

import common
from common import MACHINES_DIR
from monitoring import sweep_monitor
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
        except Exception, e:
            log("Error %s" % e) 

def async_monitor(root_directory):
    
    
    log("monitoring machines in '%s'"% (root_directory) )
    
    try:
        
        p = multiprocessing.Process(target=monitor, args=(root_directory, ) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Error %s" % e)    

def run(root_directory):
    
    try:
        async_monitor(root_directory)
    except Exception, e:
        log("Monitoring ERROR [%s]" % e)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        root_directory = sys.argv[1]
    root_directory =  MACHINES_DIR
    
    try:
        
        log("Cloudsim_monitor daemon started pid %s" % os.getpid())
        run(root_directory)
        
    except Exception, e:
        log("Cloudsim error: %s" %  e)
        
        