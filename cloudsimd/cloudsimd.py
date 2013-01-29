#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import sys
import time

import multiprocessing
from json import loads
import redis
import json

from launchers.launch_utils import RedisPublisher

import launchers


#from common import Machine

from launchers.launch_utils import get_unique_short_name

MACHINES_DIR = '/var/www-cloudsim-auth/machines'

from common import BOTO_CONFIG_FILE_USEAST
from common.web import get_cloudsim_version_txt

import traceback

from launchers import vpc_trio
from launchers import simulator
from launchers import vpc_micro_trio
from launchers import cloudsim


from launchers.launch_utils import get_constellations
from launchers.launch_utils import get_constellation_data


def list_constellations():
    r = redis.Redis()
    x = [json.loads(r.get(x)) for x in r.keys()]
    
    return x
#
# The plugins contains the function pointers for each type of constellation
# Don't forget to register new constellations
#
plugins = {}
plugins['vpc_micro_trio'] = {'launch':vpc_micro_trio.launch,    'terminate':vpc_micro_trio.terminate,    'monitor':vpc_micro_trio.monitor,   'start_simulator':vpc_micro_trio.start_simulator,   'stop_simulator':vpc_micro_trio.stop_simulator}
plugins['vpc_trio'] =       {'launch':vpc_trio.launch,          'terminate':vpc_trio.terminate,          'monitor':vpc_trio.monitor,         'start_simulator':vpc_trio.start_simulator,         'stop_simulator':vpc_trio.stop_simulator}
plugins['simulator'] =       {'launch':simulator.launch,          'terminate':simulator.terminate,       'monitor':simulator.monitor,         'start_simulator':simulator.start_simulator,         'stop_simulator':simulator.stop_simulator}
plugins['cloudsim'] =       {'launch':cloudsim.launch,          'terminate':cloudsim.terminate,       'monitor':cloudsim.monitor,         'start_simulator':cloudsim.start_simulator,         'stop_simulator':cloudsim.stop_simulator}

plugins['vpc_trio_prerelease'] =       {'launch':vpc_trio.launch_prerelease,          'terminate':vpc_trio.terminate,          'monitor':vpc_trio.monitor,         'start_simulator':vpc_trio.start_simulator,         'stop_simulator':vpc_trio.stop_simulator}
plugins['simulator_prerelease'] =       {'launch':simulator.launch_prerelease,          'terminate':simulator.terminate,       'monitor':simulator.monitor,         'start_simulator':simulator.start_simulator,         'stop_simulator':simulator.stop_simulator}


class LaunchException(Exception):
    pass

class UnknownConfig(LaunchException):
    pass
   
    
def log(msg, chan="cloudsim_log"):
    try:
        
        print ("LOG: %s" % msg)
        red = redis.Redis()
        red.publish(chan, msg)
    except Exception, e:
        pass


def list_constellations():
    r = redis.Redis()
    x = [json.loads(r.get(x)) for x in r.keys()]
    
    return x


def launch( username, 
            config, 
            constellation_name,
            credentials_ec2, 
            constellation_directory):
    
    red = redis.Redis()
        
    try:
        proc = multiprocessing.current_process().name
        #log("cloudsimd.py launch")
        log("Launching constellation %s, config '%s' for user '%s' from proc '%s'" % (constellation_name, config,  username, proc)) 
        
        launch = plugins[config]['launch']
        v = get_cloudsim_version_txt()
        gmt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        
        tags = {'username': username, 
               'constellation_name':constellation_name, 
               'CloudSim': v, 
               'GMT': gmt}
        
        launch(username, constellation_name, tags, credentials_ec2, constellation_directory)
        
        log("Launch of constellation %s done" % constellation_name)
        
    except Exception, e:
        log("cloudsimd.py launch error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 
    
    
"""
Terminates the machine via the cloud interface. Files will be removed by the 
monitoring process
"""
def terminate(username, 
              constellation, 
              credentials_ec2,
              constellation_directory):
 
    proc = multiprocessing.current_process().name
    log("terminate '%s' for '%s' from proc '%s'" % (constellation, username, proc))

    try:
        
        data = get_constellation_data(username, constellation)
        config = data['configuration']
        log("    configuration is '%s'" % (config))
        
        terminate = plugins[config]['terminate']
        terminate(username, constellation, credentials_ec2, constellation_directory)
        
        
    except Exception, e:
        log("cloudsimd.py terminate error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 
    data = get_constellation_data(username, constellation)
    data['constellation_state'] = 'terminated'
    get_constellation_data(username, constellation, data, 360)
        

def start_simulator(username, config, constellation, machine_name, package_name, launch_file_name, launch_arg, credentials_ec2, root_directorys):

    try:
        start_simulator  = plugins[config_name]['start_simulator']
        start_simulator(username, constellation, machine_name, package_name, launch_file_name, launch_args, credentials_ec2, root_directory)
    except Exception, e:
        log("cloudsimd.py start_simulator error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 


def stop_simulator(username, config, constellation,  machine):
    try:
        root_directory =  MACHINES_DIR
        stop_simulator  = plugins[config_name]['stop_simulator']
        stop_simulator(username, constellation, machine, root_directory)
    except Exception, e:
        log("cloudsimd.py stop_simulator error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
            

def monitor(username, config, constellation_name, credentials_ec2):
    
    proc = multiprocessing.current_process().name
    log("monitoring [%s] %s/%s from proc '%s'" % (config, username, constellation_name, proc))   
    try:
        done = False
        monitor = plugins[config]['monitor']
        counter = 0
        while not done:
            try:
                #log("monitor %s (%s)" % (constellation_name, counter) )
                done = monitor(username, constellation_name, credentials_ec2, counter)
                #log("monitor return value %s" % ( done) )
                counter += 1
            except Exception, e:
                done = False
                log("cloudsimd.py monitor error: %s" % e)
                tb = traceback.format_exc()
                log("traceback:  %s" % tb)
            
        log("monitor %s from proc %s DONE" % (proc, constellation_name) )    
    except Exception, e:
        log("cloudsimd.py terminate error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 

def async_monitor(username, config, constellation_name, boto_path):
    
    log("cloudsimd async_monitor [config %s] %s/%s"% (config, username, constellation_name) )
    try:
        p = multiprocessing.Process(target=monitor, args=(username, config, constellation_name, boto_path) )
        p.start()
    except Exception, e:
        log("cloudsimd async_monitor Error %s" % e)
        
    
def async_launch(username, config, constellation_name, credentials_ec2, constellation_directory):
    
    log("cloudsimd async_launch %s [config %s for user %s]"% (constellation_name, config, username) )
    try:
        p = multiprocessing.Process(target=launch, args=(username, config, constellation_name, credentials_ec2, constellation_directory ))
        p.start()
    except Exception, e:
        log("cloudsimd async_launch Error %s" % e)

def async_terminate(username, constellation, credentials_ec2, constellation_directory):
    
    log("async terminate '%s' for '%s'"% (constellation, username) )
    try:
        
        p = multiprocessing.Process(target=terminate, args= (username, constellation, credentials_ec2, constellation_directory)  )
        p.start()

    except Exception, e:
        log("Cloudsim async_terminate Error %s" % e)


                
def async_start_simulator(username, config, constellation, machine, package_name, launch_file_name,launch_args, credentials_ec2, root_directory ):
    
    
    log("async start simulator! user %s machine %s, pack %s launch %s args '%s'" % (username, machine, package_name, 
                                                                                    launch_file_name, launch_args ))
    try:
        p = multiprocessing.Process(target=start_simulator, args=(username, config, constellation, machine, package_name, launch_file_name, launch_args, credentials_ec2, root_directory ) )
        p.start()
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)

def async_stop_simulator(username, config, constellation, machine):
    log("async stop simulator! user %s machine %s" % (username, machine))
    try:
        p = multiprocessing.Process(target=stop_simulator, args=(username, config, constellation,  machine) )
        # jobs.append(p)
        p.start()
    except Exception, e:
        log("Cloudsim daemon Error %s" % e)
    
    
def tick_monitor(tick_interval):
    count = 0
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    log("ticks from proc '%s'" % (proc))
    while True:
        count +=1
        time.sleep(tick_interval)
        tick = {}
        tick['count'] = count
        tick['type'] = 'tick'
        tick['interval'] = tick_interval
        msg = json.dumps(tick)
        red.publish("cloudsim_tick", msg)


def async_tick_monitor(tick_interval):
    log("async_tick_monitor [%s secs]" % tick_interval)
    try:
        p = multiprocessing.Process(target=tick_monitor, args=( tick_interval,  )   )
        p.start()
    except Exception, e:
        log("Cloudsim tick  %s" % e)


def resume_monitoring(boto_path, root_dir): 
    log("resume_monitoring")
    constellation_names  = get_constellations()
    log("existing constellations %s" % constellation_names)
    for domain, constellation_name in constellation_names:
        try:
            log("   constellation %s/%s " %  (domain, constellation_name) )  
            constellation = get_constellation_data(domain,  constellation_name)
            state = constellation['constellation_state']
            config = constellation['configuration']
            username = constellation['username']
            log ("      config %s" % config)
            log ("      state %s" % state)
            if state != "terminated":
                async_monitor(username, config, constellation_name, boto_path)
        except Exception, e:
            print ("MONITOR ERROR %s in constellation : %s" % (e, constellation_name))
            tb = traceback.format_exc()
            log("traceback:  %s" % tb) 
            
def run(boto_path, root_dir, tick_interval):
    
    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")
    
    async_tick_monitor(tick_interval)
    
    resume_monitoring(boto_path, root_dir)    
    
    log("CLOUDSIMD STARTED boto_path=%s root_dir=%s" % (boto_path, root_dir ))
    for msg in ps.listen():
        log("CLOUDSIMD EVENT") 
        try:
            try:
                data = loads(msg['data'])
            except:
                continue
            
            cmd = data['command']
            username = data['username']
            # config = data['configuration']

            log("             CMD= \"%s\" DATA=\"%s\" " % (cmd,data) )
     
            if cmd == 'launch':
                config = data['configuration']
                # log("CLOUDSIM Launch %s" % config)
                constellation_name =  "c" + get_unique_short_name()
                
                constellation_path = os.path.join(root_dir, constellation_name )
                os.makedirs(constellation_path)
                
                async_launch(username, config, constellation_name, boto_path, constellation_path)
                async_monitor(username, config,constellation_name, boto_path)
                continue
            
            constellation = data['constellation']
            constellation_path = os.path.join(root_dir, constellation )
            
            if cmd == 'terminate':
                async_terminate(username, constellation, boto_path, constellation_path )
                continue
            
            machine = data['machine']
            if cmd == "start_simulator" :
                package_name = data['package_name']
                launch_file_name = data['launch_file_name'] 
                launch_args = data['launch_args']
                async_start_simulator(username, config, constellation, machine, package_name, launch_file_name, launch_args, boto_path, constellation_path) 
                continue
            
            if cmd == "stop_simulator" :
                async_stop_simulator(username, config, constellation, machine, boto_path, constellation_path)
                continue
            
            
        except Exception, e:
            log("Error processing message [%s]" % msg)
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)             
            

if __name__ == "__main__":
    
    try:
        
        log("Cloudsim daemon started pid %s" %  os.getpid())
        log("args: %s" % sys.argv)
        
        tick_interval = 5
        
        boto_path = os.path.abspath(BOTO_CONFIG_FILE_USEAST)
        root_dir  = os.path.abspath(MACHINES_DIR)
        
        if len(sys.argv) > 1:
           boto_path = os.path.abspath(sys.argv[1])
        if len(sys.argv) > 2:
           root_dir = os.path.abspath(sys.argv[2])

        run(boto_path, root_dir, tick_interval)
        
    except Exception, e:
        log("cloudsimd.py error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 
