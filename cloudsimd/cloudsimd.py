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

from launchers.launch_utils import SshClient

#from common import Machine

from launchers.launch_utils import get_unique_short_name
from launchers.launch_utils.launch_db import ConstellationState
from launchers.launch_utils.launch_db import get_cloudsim_config, set_cloudsim_config


import traceback

from launchers import vpc_trio
from launchers import simulator
from launchers import vpc_micro_trio
from launchers import cloudsim


from launchers.launch_utils import get_constellation_names
from launchers.launch_utils import get_constellation_data
from launchers.launch_utils import set_constellation_data
from launchers.launch_utils.launch import aws_connect



def launch_constellation(username, configuration, count =1):
    """
    Launches one (or count) constellation of a given configuration
    """
    r = redis.Redis()
    for i in range(count):
        time.sleep(0.1)
        d = {}
        d['username'] = username
        d['command'] = 'launch'
        d['configuration'] = configuration
        s = json.dumps(d)
        print(i, ")", s)
        r.publish('cloudsim_cmds', s)
        
def terminate_all_constellations():
    for x in get_constellation_names():
        d = {}
        d['username'] = 'hugo@osrfoundation.org'
        d['command'] = 'terminate'
        d['constellation'] = x
        s = json.dumps(d)
        time.sleep(0.5)
        print("Terminate %s" % x)
        r.publish('cloudsim_cmds', s)


def del_constellations():
    """
    Removes all constellations from the Redis db 
    does not attempt to terminate them
    """
    r = redis.Redis()
    for k in r.keys():
        if k.find('cloudsim/') == 0:
            r.delete(k)
    # r.flushdb()

def list_constellations():
    """
    Returns a list that contains all the constellations in the Redis db
    """
    r = redis.Redis()
    constellations = []
    for key in r.keys():
        s = r.get(key)
        if key.find('cloudsim/') == 0:
            c = json.loads(s)
            constellations.append(c)
    return constellations 
    

def get_aws_instance_by_name(instance_name, boto_path="../../boto.ini"):
    """
    Interactive command to get a bot instance of a running machine
    Raises exceptions if the credentials are not there or invalid
    """
    ec2conn = aws_connect(boto_path)[0]
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if id.tags.has_key('Name'):
            name = id.tags['Name']
            if name == instance_name:
                return i
    return None

def get_aws_instance(instance, boto_path="../../boto.ini"):
    """
    Interactive command to get a boto instance of a running machine
    instance: a string that contains the AWS instance id
    Raises exceptions if the credentials are not there or invalid
    """
    ec2conn = aws_connect(boto_path)[0]
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if i.id == instance:
            return i
    return None
        
#
# The plugins contains the function pointers for each type of constellation
# Don't forget to register new constellations
#

plugins = {}
plugins['vpc_micro_trio'] = {'launch':vpc_micro_trio.launch,    
                             'terminate':vpc_micro_trio.terminate,    
                             'monitor':vpc_micro_trio.monitor,   
                             'start_task':vpc_micro_trio.start_task,   
                             'stop_task':vpc_micro_trio.stop_task}

plugins['vpc_trio'] =       {'launch':vpc_trio.launch,
                             'terminate':vpc_trio.terminate,          
                             'monitor':vpc_trio.monitor,         
                             'start_task':vpc_trio.start_task,         
                             'stop_task':vpc_trio.stop_task}

plugins['simulator'] =       {'launch':simulator.launch,          
                              'terminate':simulator.terminate,       
                              'monitor':simulator.monitor,         
                              'start_task':simulator.start_task,         
                              'stop_task':simulator.stop_task}

plugins['cloudsim'] =       {'launch':cloudsim.launch,          
                             'terminate':cloudsim.terminate,       
                             'monitor':cloudsim.monitor,         
                             'start_task':cloudsim.start_task,         
                             'stop_task':cloudsim.stop_task}

plugins['vpc_trio_prerelease'] =  {'launch':vpc_trio.launch_prerelease,          
                                    'terminate':vpc_trio.terminate_prerelease,          
                                    'monitor':vpc_trio.monitor_prerelease,         
                                    'start_task':vpc_trio.start_simulator,         
                                    'stop_task':vpc_trio.stop_task}

plugins['simulator_prerelease'] =   {'launch':simulator.launch_prerelease,          
                                     'terminate':simulator.terminate_prerelease,       
                                     'monitor':simulator.monitor_prerelease,         
                                     'start_task':simulator.start_simulator,         
                                     'stop_task':simulator.stop_task}


class LaunchException(Exception):
    pass

class UnknownConfig(LaunchException):
    pass
   
    
def log(msg, chan="cloudsimd"):
    try:
        
        print ("LOG: %s" % msg)
        red = redis.Redis()
        red.publish(chan, msg)
    except Exception, e:
        pass


def launch( username, 
            config, 
            constellation_name,
            credentials_ec2, 
            constellation_directory):

    constellation = ConstellationState(constellation_name)
    try:
        proc = multiprocessing.current_process().name
        
        cloudsim_config = get_cloudsim_config()
        version = cloudsim_config['cloudsim_version']
        
        #log("cloudsimd.py launch")
        log("CloudSim [%s] Launching constellation [%s], config [%s] for user [%s] from proc [%s]" % (version, constellation_name, config,  username, proc)) 
        
        launch = plugins[config]['launch']
        
        gmt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
        
        tags = {'username': username, 
               'constellation_name':constellation_name, 
               'CloudSim': version, 
               'GMT': gmt}

        constellation.set_value('username', username)
        constellation.set_value('constellation_name', constellation_name)
        constellation.set_value('gmt', gmt)
        constellation.set_value('configuration', config)
        constellation.set_value('constellation_directory', constellation_directory)
        constellation.set_value('constellation_state', 'launching')
        constellation.set_value('error', '')
        
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])
        
        try:
            launch(username, constellation_name, tags, credentials_ec2, constellation_directory)
        except Exception, e:
            error_msg = constellation.get_value('error')
            
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)
            terminate(username, constellation_name, credentials_ec2, constellation_directory)
            constellation.set_value('error', '%s' % error_msg)
            constellation.expire(10)
            raise
        
        log("Launch of constellation %s done" % constellation_name)
        
    except Exception, e:
        
        log("cloudsimd.py launch error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)

        #terminate(username, constellation_name, credentials_ec2, constellation_directory)
    
    
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
        
        data = get_constellation_data( constellation)
        config = data['configuration']
        log("    configuration is '%s'" % (config))
        
        terminate = plugins[config]['terminate']
        terminate(username, constellation, credentials_ec2, constellation_directory)
        
        
    except Exception, e:
        log("cloudsimd.py terminate error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 
        
    constellation = ConstellationState(constellation)
    constellation.set_value('constellation_state', 'terminated')    
    log("Deleting %s from the database" % constellation)
    constellation.expire(30)    



task_states = ['ready', 'setup', 'running', 'teardown', 'finished']

def create_task(constellation_name, data):
    try:
        log('create_task')
        task_id = "t" + get_unique_short_name()
        data['task_id'] = task_id
        data['task_state'] = "ready"
        data['task_message'] = 'Ready to run'
        
    #    for k,v in data.iteritems():
    #        log('  %s = %s' % (k,v))
        
        cs = ConstellationState(constellation_name)
        tasks = cs.get_value('tasks')
        tasks.append(data)
        
        # save new task list in db
        cs.set_value('tasks', tasks)
        log('task %s/%s created' % (constellation_name, task_id))
    except Exception, e:
        log("update_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)

def update_task(constellation_name, data):

    #    for k,v in data.iteritems():
    #        log('  %s = %s' % (k,v))
    try:
        task_id = data['task_id']
        log("update_task %s/%s" % (constellation_name, task_id))
        cs = ConstellationState(constellation_name)
        cs.update_task(task_id, data)
#        tasks = cs.get_value('tasks')
#        task = cs.get_task(tasks, task_id)
#        task.update(data)
#        cs.set_value('tasks', tasks)
        log("updated: %s" % task)
    except Exception, e:
        log("update_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
    
    
def delete_task(constellation_name, task_id):
    log('delete task')
    try:
        log("delete_task %s/%s" % (constellation_name, task_id))
        cs = ConstellationState(constellation_name)
        cs.delete_task(task_id)

    except Exception, e:
        log("delete_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)

def start_task(constellation_name, task_id):
    try:
        log("start_task %s/%s" % (constellation_name, task_id))
        cs = ConstellationState(constellation_name)
        config = cs.get_value('configuration')
        start_task = plugins[config]['start_task']
        current_task = cs.get_value('current_task')
        if current_task == '':
            task = cs.get_task(task_id)
            task_state = task['task_state']
            if task_state == 'ready':
                cs.set_value('current_task', task_id)
                log('task_state running')
                task['task_state'] = 'running'
                cs.update_task(task_id, task) 
                # no other task running, and task is ready
                try:
                    start_task(constellation_name, task)
                except:
                    pass

            else:
                log("Task is not ready (%s)" % task_state)
        else:
                log("can't run task %s while tasks %s is already running" % (task_id, current_task))
    except Exception, e:
        log("start_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
                
    
def stop_task(constellation_name):
    try:
        log("stop_task %s" % (constellation_name))
        cs = ConstellationState(constellation_name)
        config = cs.get_value('configuration')
        stop_task_fn = plugins[config]['stop_task']
        
        task_id = cs.get_value('current_task')
        if task_id != '':
            task = cs.get_task(task_id)
            
            task['task_state'] = 'stopping'
            log('task_state stopping')
            cs.update_task(task_id, task)
            
            stop_task_fn(constellation_name)            
            
            task['task_state'] = 'stopped'
            cs.update_task(task_id, task)
            log('task_state stopped')
            cs.set_value('current_task', '')            
        else:
            log('stop_task error: no current task')    
    except Exception, e:
        log("stop_task error %s" % e)
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
                log("monitor return value %s" % ( done) )
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
    
    log("cloudsimd async_launch '%s' [config '%s' for user '%s']"% (constellation_name, config, username) )
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
    constellation_names  = get_constellation_names()
    log("existing constellations %s" % constellation_names)
    for constellation_name in constellation_names:
        try:
            log("   constellation %s " %  (constellation_name) )  
            constellation = get_constellation_data( constellation_name)
            state = constellation['constellation_state']
            config = constellation['configuration']
            username = constellation['username']
            log ("      resume_monitoring config %s" % config)
            log ("      resume_monitoring state %s" % state)
            async_monitor(username, config, constellation_name, boto_path)
        except Exception, e:
            print ("MONITOR ERROR %s in constellation : %s" % (e, constellation_name))
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)
            
            
def run_tc_command(_username, _constellationName, _targetPacketLatency):  

    constellation = get_constellation_data( _constellationName)
    config = constellation['configuration']
    keyDirectory = os.path.join(constellation['constellation_directory'])
        
    if (config == 'simulator_prerelease') or (config == 'simulator'):
        keyDirectory = os.path.join(keyDirectory, constellation['sim_machine_name'])
        keyPairName = constellation['sim_key_pair_name']
        ip = constellation['simulation_ip']
    elif (config == 'vpc_trio_prerelease') or (config == 'vpc_trio') or (config == 'vpc_micro_trio'):
        keyDirectory = os.path.join(keyDirectory, 'router_' + _constellationName)
        keyPairName = constellation['router_key_pair_name']
        ip = constellation['router_public_ip']
    else:
        #You should not be here
        log("cloudsim::run_tc_command() Unknown constellation type: (%s)" % (config) )
        return
    
    cmd = 'redis-cli set ts_targetLatency ' + str(_targetPacketLatency)
    ssh = SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    ssh.cmd(cmd)                   
    
def async_create_task(constellation_name, data):
    log('async_create_task')
#    for k,v in data.iteritems():
#        log('  %s = %s' % (k,v))
            
    p = multiprocessing.Process(target= create_task, 
                                args=(constellation_name, data ) )
    p.start()

def async_update_task(constellation_name, data):
    log('async_update_task')
    p = multiprocessing.Process(target= update_task, 
                                args=(constellation_name, data ) )
    p.start()

def async_delete_task(constellation_name, task_id):
    p = multiprocessing.Process(target= delete_task, 
                                args=(constellation_name, 
                    task_id ) )
    p.start()

def async_start_task(constellation_name, task_id):
    p = multiprocessing.Process(target= start_task, 
                                args=(constellation_name, 
                    task_id ) )
    p.start()

def async_stop_task(constellation_name):
    p = multiprocessing.Process(target= stop_task, 
                                args=(constellation_name, ))
    p.start()
         
def run(boto_path, root_dir, tick_interval):
    
    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")
    
    async_tick_monitor(tick_interval)
    
    resume_monitoring(boto_path, root_dir)    
    
    log("CLOUDSIMD STARTED boto_path=%s root_dir=%s" % (boto_path, root_dir ))
    for msg in ps.listen():
        log("=== CLOUDSIMD EVENT ===") 
        try:
            try:
                data = loads(msg['data'])
            except:
                continue
            
            cmd = data['command']
            
            # config = data['configuration']

            log("CMD= \"%s\" DATA=\"%s\" " % (cmd,data) )
     
            if cmd == 'launch':
                username = data['username']
                config = data['configuration']
                # log("CLOUDSIM Launch %s" % config)
                constellation_name =  "c" + get_unique_short_name()
                
                constellation_path = os.path.join(root_dir, constellation_name )
                os.makedirs(constellation_path)
                
                async_launch(username, config, constellation_name, boto_path, constellation_path)
                async_monitor(username, config,constellation_name, boto_path)
                continue

            constellation = data['constellation']
            
            
            if cmd == 'terminate':
                username = data['username']
                constellation_path = os.path.join(root_dir, constellation )
                async_terminate(username, constellation, boto_path, constellation_path )
                continue
            #
            # tasks stuff
            #
            if cmd == 'create_task':
                data.pop('constellation')
                data.pop('command')
                async_create_task(constellation, data)
            
            if cmd == "update_task":
                data.pop('constellation')
                data.pop('command')
                async_update_task(constellation ,data)
            
            if cmd == 'delete_task':
                task_id = data['task_id']
                async_delete_task(constellation, task_id)
            
            if cmd == 'start_task':
                log('start_task')
                task_id = data['task_id']
                log('start_task %s' % task_id)
                async_start_task(constellation, task_id)
            
            if cmd == 'stop_task':
                async_stop_task(constellation)
            
            if cmd == "start_simulator" :
                machine = data['machine']
                package_name = data['package_name']
                launch_file_name = data['launch_file_name'] 
                launch_args = data['launch_args']
                async_start_simulator(username, constellation, machine, package_name, launch_file_name, launch_args) 
                continue
            
            if cmd == "stop_simulator" :
                machine = data['machine']
                async_stop_simulator(username, constellation, machine)
                continue
            
            if cmd == 'update_tc' :
                targetPacketLatency = int(data['targetPacketLatency'])                             
                run_tc_command(username, constellation, targetPacketLatency)                
            
        except Exception, e:
            log("Error processing message [%s]" % msg)
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)             
            

if __name__ == "__main__":
    
    try:
        log("Cloudsim daemon started pid %s" %  os.getpid())
        log("args: %s" % sys.argv)
        
        tick_interval = 5
        
        boto_path = '/var/www-cloudsim-auth/boto-useast'
        root_dir  = '/var/www-cloudsim-auth/machines'

        if len(sys.argv) > 1:
           boto_path = os.path.abspath(sys.argv[1])
        if len(sys.argv) > 2:
           root_dir = os.path.abspath(sys.argv[2])
           
        config = {}
        config['boto_path'] = boto_path
        config['machines_directory'] = root_dir
        config['cloudsim_version'] = '1.x.x'
        set_cloudsim_config(config)
        
        run(boto_path, root_dir, tick_interval)
        
    except Exception, e:
        log("cloudsimd.py error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb) 
