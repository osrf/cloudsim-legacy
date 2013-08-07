#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import sys
import time
import shutil
import multiprocessing
from json import loads
import redis
import json
import logging

from launchers.launch_utils import SshClient

#from common import Machine

from launchers.launch_utils import get_unique_short_name
from launchers.launch_utils.launch_db import ConstellationState
from launchers.launch_utils.launch_db import get_cloudsim_config,\
    set_cloudsim_config


import traceback


from launchers.launch_utils import get_constellation_names
from launchers.launch_utils import get_constellation_data
from launchers.launch_utils import set_constellation_data
from launchers.launch_utils import aws_connect
from launchers.launch_utils.softlayer import get_constellation_prefixes
from launchers.launch_utils import LaunchException

from launchers.launch_utils.launch_db import set_cloudsim_configuration_list
from launchers.launch_utils.launch_db import log_msg

# for interactive use
from launchers.launch_utils.softlayer import load_osrf_creds
from launchers.launch_utils.softlayer import softlayer_dash_board
from launchers.launch_utils.softlayer import softlayer_server_scan
from launchers.launch_utils.softlayer import get_machine_login_info

import datetime

try:
    logging.basicConfig(filename='/tmp/cloudsimd.log',
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                level=logging.DEBUG)
except:
    logging.basicConfig(filename='/tmp/cloudsimd_no_root.log',
                format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                level=logging.DEBUG)

def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


class UnknownConfig(LaunchException):
    pass

task_states = ['ready', 
               #'setup',
               'starting',
               'running',
               'stopping',
               #'teardown',
               'stopped']

def remove_tasks(name=None):
    """ 
    Removes tasks for constellation name. If name is None,
    tasks are removed for all running constellations.
    """
    names = []
    if name :
        names = [name]
    else:
        names = get_constellation_names()
    for constellation_name in names:
        cs = ConstellationState(constellation_name)
        cs.set_value('tasks',[])
        cs.set_value('current_task','')


def update_tasks(new_task_data, name=None):
    """
    Update all the tasks for a given constellation or all of them (if None)
    @param new_task_data Dictionary with the new task fields
    """
    names = []
    if name:
        names = [name]
    else:
        names = get_constellation_names()
    for constellation_name in names:
        cs = ConstellationState(constellation_name)
        tasks = cs.get_value('tasks')
        for task in tasks:
            task_id = task['task_id']
            for k, v in new_task_data.iteritems():
                cs.update_task_value(task_id, k, v)


def reset_tasks(name=None):
    """
    Resets tasks for constellation name. If name is None,
    tasks are reset for all running constellations.
    
    After reset, the current task is empty and any task that was
     - starting
     - running
     - stopping
    set to stopped, and it can't be run again.
    Stopped tasks are not affected
    """
    names = []
    if name :
        names = [name]
    else:
        names = get_constellation_names()
    for constellation_name in names:
        cs = ConstellationState(constellation_name)
        cs.set_value('current_task','')
        tasks = cs.get_value('tasks')
        for task in tasks:
            task_id = task['task_id']
            state = task['task_state']
            if state not in ['ready', 'stopped']:
                cs.update_task_value(task_id, 'task_state', 'stopped')


def launch_constellation(username, configuration, args=None):
    """
    Launches one (or count) constellation of a given configuration
    """
    r = redis.Redis()

    d = {}
    d['username'] = username
    d['command'] = 'launch'
    d['configuration'] = configuration
    if args:
        d['args'] = args

    s = json.dumps(d)
    print("LAUNCH constellation... command: %s " % s)
    r.publish('cloudsim_cmds', s)


def terminate_all_constellations():
    r = redis.Redis()

    for x in get_constellation_names():
        d = {}
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


class ConstellationPlugin(object):
    """
    The plugins contains the function pointers for each type of constellation
    Don't forget to register new constellations
    """
    def __init__(self, launch, terminate, update, monitor, 
                 start_task,
                 stop_task):
        self.launch = launch
        self.terminate = terminate
        self.update = update
        self.monitor = monitor
        self.start_task = start_task
        self.stop_task = stop_task


def get_plugin(configuration):
    """
    Each type of constellation has a plugin that implements the details of
    launch-terminate and start-stop simulation.
    This is the switch.
    """
#     def make_plugin(module):
#         ConstellationPlugin(module.launch, module.terminate, module.update,
#                             module.monitor,
#                             module.start_task,
#                             module.stop_task)
        
    plugin = None
    #log("get_plugin '%s'" % configuration)


    if configuration.startswith("OSRF CloudSim ") or configuration == "AWS CloudSim":
        from launchers import cloudsim as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.update, c.monitor,
                              None, None)

    elif configuration.startswith("OSRF VRC Constellation "):
        from launchers import vrc_contest as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.update, c.monitor,
                                     c.start_task, c.stop_task)

#     elif configuration == 'AWS CloudSim':
#         #return make_plugin(launchers.amazon_cloudsim)
#          from launchers import amazon_cloudsim as c
#          plugin = ConstellationPlugin(c.launch, c.terminate, c.update, c.monitor,
#                                       c.start_task, c.stop_task)
    elif configuration == 'AWS simulator':
        from launchers import simulator as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.update, c.monitor,
                                     c.start_task, c.stop_task)

    elif configuration.startswith('AWS DRC'):
        #from launchers import amazon_trio as c
        from launchers import vrc_contest as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.update, c.monitor,
                                     c.start_task, c.stop_task)

    else:
        raise UnknownConfig('Invalid configuration "%s"' % (configuration,))
    
    log("get_plugin: %s %s" % (configuration, plugin))
    return plugin


def _load_cloudsim_configurations_list():
    """
    Loads the available configurations depending on the credentials. 
     - AWS constellations if AWS credentials are available
     - A list of constellations for SoftLayer credentials
     This function is called upon CloudSim startup, and as a redis command
     (After credentials are overwritten by the web app, for example)
    """

    configs = {}
    
    
    config = get_cloudsim_config()
    
    boto_path = config['boto_path']
    if os.path.exists(boto_path):
        configs['AWS DRC'] = {'description': "DRC competition: a router and a GPU simulator, using gazebo and drcsim packages"}
        configs['AWS DRC with FC'] = {'description': "DRC competition: a router and 2 GPU machines: a simulator and a Field computer, using gazebo and drcsim packages"}
        #configs['AWS simulator'] = {'description': "1 machine for using gzserver on the cloud: GPU computer with the latest ros-fuerte, gazebo and drcsim packages installed"}
        configs['AWS CloudSim'] = {'description': "1 machine for starting a CloudSim on the cloud: A micro instance web app clone"}

    cloudsim_prefixes = []
    const_prefixes = []
    
    osrf_creds_path = config['softlayer_path']
    try:
        try:
            osrf_creds = load_osrf_creds(osrf_creds_path)
        except Exception, e:
            log("SoftLayer credentials loading error: %s" % e)

        cloudsim_prefixes, const_prefixes = get_constellation_prefixes(osrf_creds)
        log("softlayer constellations: %s" % const_prefixes)
        log("softlayer cloudsims: %s" % cloudsim_prefixes)
    except Exception, e:
        log("Error enumerating machines %s" % e)
        pass
    
    for prefix in cloudsim_prefixes:
        configs['OSRF CloudSim %s' % prefix] = {'description': "DARPA VRC Challenge CloudSim server complete install"}
        #configs['OSRF CloudSim update %s' % prefix] = {'description': "DARPA VRC Challenge CloudSim update only"}
        
    for prefix in const_prefixes:
        configs['OSRF VRC Constellation %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
        configs['OSRF VRC Constellation nightly build %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
        configs['OSRF VRC Constellation nvidia latest %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
        configs['OSRF VRC Constellation partial %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
    set_cloudsim_configuration_list(configs)
    #log("cloudsim configurations list updated: %s" % configs)


def launch(username,
           config,
           constellation_name,
           args,
           constellation_directory):
    """
    Deploys a constellation. The configuration determines what type of
    constellation will be launched. the constellation directory is where all
    data should be saved (ssh keys, downloadable scripts, etc.)
    """

    log("launch username %s" % username)
    log("launch config %s" % config)
    log("launch constellation_name %s" % constellation_name)
    log("launch args %s" % args)
    log("launch constellation_directory %s" % constellation_directory)

    constellation = ConstellationState(constellation_name)
    try:
        proc = multiprocessing.current_process().name

        cloudsim_config = get_cloudsim_config()
        version = cloudsim_config['cloudsim_version']

        #log("cloudsimd.py launch")
        log("CloudSim [%s] Launching constellation [%s], config [%s] for user [%s] from proc [%s]" % (version, constellation_name, config,  username, proc))

        constellation_plugin = get_plugin(config)

        gmt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

        tags = {'username': username,
                'constellation_name': constellation_name,
                'CloudSim': version,
                'GMT': gmt}

        if args != None:
            tags['args'] = args

        constellation.set_value('username', username)
        constellation.set_value('constellation_name', constellation_name)
        constellation.set_value('gmt', gmt)
        constellation.set_value('configuration', config)
        constellation.set_value('constellation_directory', constellation_directory)
        constellation.set_value('error', '')

        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        try:
            constellation_plugin.launch(username, config, constellation_name, tags, constellation_directory)
        except Exception, e:
            #error_msg = constellation.get_value('error')
            constellation.set_value('error', '%s' % e)
            tb = traceback.format_exc()
            log("LAUNCH ERROR traceback:  %s" % tb)
            log("LAUNCH ERROR %s traceback:  %s" % (constellation_name, tb), "launch_errors")

            #time.sleep(10)
            #terminate(constellation_name, constellation_directory)

            #constellation.expire(10)

        else:
            log("Launch of constellation %s done" % constellation_name)

    except Exception, e:

        log("cloudsimd.py launch error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def update_constellation(constellation_name):
    """
    Updates the constellation via the cloud interface. 
    This is an operation applied to a running constellation to ugrade the
    software
    """
    proc = multiprocessing.current_process().name
    log("update_constellation '%s' from proc '%s'" % (constellation_name,  proc))

    try:

        data = get_constellation_data(constellation_name)
        config = data['configuration']
        log("    configuration is '%s'" % (config))

        constellation_plugin = get_plugin(config)
        constellation_plugin.update(constellation_name)
    except Exception, e:
        log("cloudsimd.py update error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
        log("UPDATE ERROR %s traceback:  %s" % (constellation_name, tb), "launch_errors")



def terminate(constellation_name):
    """
    Terminates the constellation via the cloud interface.
    This could give the resources back to the cloud provider (AWS), 
    or wipe data.
    """

    proc = multiprocessing.current_process().name
    log("terminate '%s' from proc '%s'" % (constellation_name,  proc))

    try:
        data = get_constellation_data(constellation_name)
        config = data['configuration']
        log("    configuration is '%s'" % (config))
        constellation_plugin = get_plugin(config)
        constellation_plugin.terminate(constellation_name)
    except Exception, e:
        log("cloudsimd.py terminate error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
        log("LAUNCH ERROR %s traceback:  %s" % (constellation_name, tb),
            "launch_errors")
            
    constellation = ConstellationState(constellation_name)
    constellation.set_value('constellation_state', 'terminated')
    log("Deleting %s from the database" % constellation_name)
    constellation.expire(1)


def create_task(constellation_name, data):
    """
    Adds a task to a constellation simulation ask list. The data is a
    dictionary. The keys are:
    - task_title
    - ros_package
    - launch_file
    - launch_args
    - timeout
    - latency
    - uplink_data_cap
    - downllink_data_cap
    - local_start
    - local_stop
    - vrc_id
    - vrc_num
    """
    try:
        log('create_task')
        task_id = "t" + get_unique_short_name()
        data['task_id'] = task_id
        data['task_state'] = "ready"
        data['task_message'] = 'Ready to run'

        cs = ConstellationState(constellation_name)
        tasks = cs.get_value('tasks')
        tasks.append(data)

        # save new task list in db
        cs.set_value('tasks', tasks)
        log('task %s/%s created' % (constellation_name, task_id))
    except Exception, e:
        log("update_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback: %s" % tb)


def update_task(constellation_name, data):
    """
    Updates a task to a constellation simulation ask list. The data is a
    dictionary. The keys are:
    - task_title
    - ros_package
    - launch_file
    - launch_args
    - timeout
    - latency
    - uplink_data_cap
    - downllink_data_cap
    - local_start
    - local_stop
    - vrc_id
    - vrc_num
    - task_id
    """
    try:
        task_id = data['task_id']
        log("update_task %s/%s" % (constellation_name, task_id))
        cs = ConstellationState(constellation_name)
        cs.update_task(task_id, data)
        log("updated: %s" % task_id)
    except Exception, e:
        log("update_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def delete_task(constellation_name, task_id):
    """
    Removes a task from the constellation's simulation task list
    """
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
    """
    Starts a simulation task on a constellation. Only one task can run at a
    time.
    """
    try:
        log("start_task %s/%s" % (constellation_name, task_id))
        cs = ConstellationState(constellation_name)
        config = cs.get_value('configuration')
        constellation_plugin = get_plugin(config)
        current_task = cs.get_value('current_task')
        if current_task == '':
            task = cs.get_task(task_id)
            task_state = task['task_state']
            if task_state == 'ready':
                cs.set_value('current_task', task_id)
                log('task_state starting')
                cs.update_task_value(task_id, 'task_message', 'Starting task')
                cs.update_task_value(task_id, 'task_state', 'starting')
                cs.update_task_value(task_id, 'start_time', datetime.datetime.utcnow().isoformat())
                # no other task running, and task is ready
                try:
                    constellation_plugin.start_task(constellation_name, task)
                except Exception, e:
                    log("Start task error %s" % e)
                    tb = traceback.format_exc()
                    log("traceback:  %s" % tb)
                    cs.update_task_value(task_id, 'task_message', 'Task failed to start: %s'%(e))
                    task = cs.get_task(task_id)
                    constellation_plugin.stop_task(constellation_name, task)
                    cs.update_task_value(task_id, 'task_state', 'stopped')
                    cs.set_value('current_task', '')
                    raise
                cs.update_task_value(task_id, 'task_state', 'running')
                log('task_state running')
            else:
                log("Task is not ready (%s)" % task_state)
        else:
                log("can't run task %s while tasks %s is already running" % (task_id, current_task))
    except Exception, e:
        log("start_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def stop_task(constellation_name):
    """
    Stops the current running tasks on a constellation. If no simulation task
    is running.
    """
    try:
        log("stop_task %s" % (constellation_name))
        cs = ConstellationState(constellation_name)
        config = cs.get_value('configuration')
        constellation_plugin = get_plugin(config)

        task_id = cs.get_value('current_task')
        if task_id != '':
            task = cs.get_task(task_id)

            # you can only stop a running task
            if task['task_state'] == 'running':

                log('task_state stopping')
                cs.update_task_value(task_id, 'task_state', 'stopping')
                cs.update_task_value(task_id, 'stop_time', datetime.datetime.utcnow().isoformat())
                try:
                    log('calling stop task')
                    constellation_plugin.stop_task(constellation_name, task)
                except Exception, e:
                    tb = traceback.format_exc()
                    log('task error during stop')
                    log("traceback:  %s" % tb)
                else:
                    log('task stopped successfully')
                finally:
                    cs.update_task_value(task_id, 'task_state', 'stopped')
                    cs.set_value('current_task', '')
            else:
                log("""stop_taks error: wrong state "%s" for task "%s" """ % (task['task_state'], task_id))
        else:
            log('stop_task error: no current task')
    except Exception, e:
        log("stop_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def monitor(config, constellation_name):
    """
    Loop that monitors the execution of a constellation
    """
    proc = multiprocessing.current_process().name
    log("monitoring [%s] %s from proc '%s'" % (config,
                                               constellation_name,
                                               proc))
    try:
        done = False
        constellation_plugin = get_plugin(config)
        counter = 0
        while not done:
            try:
                log("monitor %s (%s)" % (constellation_name, counter) )
                done = constellation_plugin.monitor(constellation_name, counter)
                #log("monitor return value %s" % ( done) )
                counter += 1
            except Exception, e:
                done = False
                log("cloudsimd.py monitor error: %s" % e)
                tb = traceback.format_exc()
                log("traceback:  %s" % tb)

        log("monitor %s from proc %s DONE" % (proc, constellation_name))
    except Exception, e:
        log("cloudsimd.py monitor error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
        
    log("END OF MONITOR %s" % constellation_name)


def async_monitor(config, constellation_name):

    log("cloudsimd async_monitor [config %s] %s" % (config,  constellation_name))
    try:
        p = multiprocessing.Process(target=monitor, 
                                    args=(config, constellation_name))
        p.start()
    except Exception, e:
        log("cloudsimd async_monitor Error %s" % e)


def async_launch(username, config, constellation_name, args,  constellation_directory):

    log("cloudsimd async_launch '%s' [config '%s' for user '%s']" % (constellation_name, config, username))
    try:
        p = multiprocessing.Process(target=launch, args=(username, config, constellation_name, args, constellation_directory))
        p.start()
    except Exception, e:
        log("cloudsimd async_launch Error %s" % e)


def async_update(constellation_name):

    log("async update '%s'" % (constellation_name))
    try:
        p = multiprocessing.Process(target=update_constellation, args=(constellation_name,))
        p.start()

    except Exception, e:
        log("Cloudsim async_update Error for constellation %s :%s" % (constellation_name,e))


def async_terminate(constellation):

    log("async terminate '%s'" % (constellation,))
    try:
        p = multiprocessing.Process(target=terminate, args=(constellation,))
        p.start()

    except Exception, e:
        log("Cloudsim async_terminate Error %s" % e)


def tick_monitor(tick_interval):
    count = 0
    red = redis.Redis()
    proc = multiprocessing.current_process().name
    log("ticks from proc '%s'" % (proc))
    while True:
        count += 1
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
        p = multiprocessing.Process(target=tick_monitor, args=(tick_interval,))
        p.start()
    except Exception, e:
        log("Cloudsim tick  %s" % e)


def resume_monitoring(root_dir):
    log("resume_monitoring")
    constellation_names = get_constellation_names()
    log("existing constellations %s" % constellation_names)
    for constellation_name in constellation_names:
        try:
            log("   constellation %s " % (constellation_name))
            constellation = get_constellation_data(constellation_name)
            state = constellation['constellation_state']
            config = constellation['configuration']
            log("      resume_monitoring config %s" % config)
            log("      resume_monitoring state %s" % state)
            async_monitor(config, constellation_name)
        except Exception, e:
            print ("MONITOR ERROR %s in constellation : %s" % (e, constellation_name))
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)


def run_tc_command(_username, _constellationName, _targetPacketLatency):

    constellation = get_constellation_data(_constellationName)
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
        log("cloudsim::run_tc_command() Unknown constellation type: (%s)" % (config))
        return

    cmd = 'redis-cli set vrc_target_outbound_latency ' + str(_targetPacketLatency)
    ssh = SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    ssh.cmd(cmd)


def async_create_task(constellation_name, data):
    log('async_create_task')
#    for k,v in data.iteritems():
#        log('  %s = %s' % (k,v))

    p = multiprocessing.Process(target=create_task,
                                args=(constellation_name, data))
    p.start()


def async_update_task(constellation_name, data):
    log('async_update_task')
    p = multiprocessing.Process(target=update_task,
                                args=(constellation_name, data))
    p.start()


def async_delete_task(constellation_name, task_id):
    p = multiprocessing.Process(target=delete_task,
                                args=(constellation_name, task_id))
    p.start()


def async_start_task(constellation_name, task_id):
    p = multiprocessing.Process(target=start_task,
                                args=(constellation_name, task_id))
    p.start()


def async_stop_task(constellation_name):
    p = multiprocessing.Process(target=stop_task,
                                args=(constellation_name,))
    p.start()


def async_update_cloudsim_configuration_list():
    p = multiprocessing.Process(target=_load_cloudsim_configurations_list,
                                args=())
    p.start()


def launch_cmd(root_dir, data):

    username = data['username']
    config = data['configuration']
    # extra arguments to the launch methd
    args = None
    if data.has_key('args'):
        args = data['args']

    if config.startswith("AWS"):
        # number of constellations to create
        count = 1
        if data.has_key('count'):
            count = int(data['count'])
        # log("CLOUDSIM Launch %s" % config)
        for i in range(count):
            constellation_name = "c" + get_unique_short_name()
            constellation_path = os.path.join(root_dir, constellation_name)
            os.makedirs(constellation_path)
            cs = ConstellationState(constellation_name)
            cs.set_value('constellation_state', 'launching')
            async_launch(username, config, constellation_name, args,
                         constellation_path)
            async_monitor(config, constellation_name)


        
    elif config.startswith("OSRF"):
        partial_upgrade = False
        if config.find('partial') > 0:
            partial_upgrade = True

        constellation_name = config.replace(" ", "_")
        constellation_name = constellation_name.replace("_partial", "")
        constellation_name = constellation_name.replace("_nvidia_latest", "")
        constellation_name = constellation_name.replace("_nightly_build", "")
        constellation_path = os.path.join(root_dir, constellation_name)

        if os.path.exists(constellation_path):
            constellation_backup = "%s-%s" % (get_unique_short_name(),
                                              constellation_name, )

            backup_path = os.path.join(root_dir, constellation_backup)
            log("move %s to %s" % (constellation_path, backup_path))
            shutil.move(constellation_path, backup_path)

            # create the directory
            os.makedirs(constellation_path)
            
            # move exiting zip keys to new direcory
            if partial_upgrade:
                for fname in ['key-fc1.pem','key-fc1.pem.pub',
                              'key-fc2.pem','key-fc2.pem.pub']:
                    src = os.path.join(backup_path, fname)
                    log("move %s to %s" % (src, constellation_path))
                    shutil.copy(src, constellation_path)
                    dst = os.path.join(constellation_path, fname)
                    assert(os.path.exists(dst))
        else:
            os.makedirs(constellation_path)

        async_launch(username, config,
                     constellation_name, args,
                     constellation_path)

        async_monitor(config, constellation_name)


def run(root_dir, tick_interval):

    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")

    async_tick_monitor(tick_interval)
    resume_monitoring(root_dir)

    log("CLOUDSIMD STARTED root_dir=%s" % (root_dir))
    log("Ready to get commands")
    red.set('cloudsim_ready', True)
    for msg in ps.listen():

        
        log("=== CLOUDSIMD EVENT ===") 
        try:
            try:
                data = loads(msg['data'])
            except:
                continue

            cmd = data['command']
            # config = data['configuration']

            log("CMD= \"%s\" DATA=\"%s\" " % (cmd, data))

            if cmd == '_load_cloudsim_configurations_list':
                async_update_cloudsim_configuration_list()

            elif cmd == 'launch':
                launch_cmd(root_dir, data)

            elif cmd == 'terminate':
                constellation = data['constellation']
                async_terminate(constellation)

            elif cmd == 'update':
                constellation = data['constellation']
                async_update(constellation)

            #
            # tasks stuff
            #
            elif cmd == 'create_task':
                constellation = data['constellation']
                data.pop('constellation')
                data.pop('command')
                async_create_task(constellation, data)

            elif cmd == "update_task":
                constellation = data['constellation']
                data.pop('constellation')
                data.pop('command')
                async_update_task(constellation, data)

            elif cmd == 'delete_task':
                constellation = data['constellation']
                task_id = data['task_id']
                async_delete_task(constellation, task_id)

            elif cmd == 'start_task':
                log('start_task')
                constellation = data['constellation']
                task_id = data['task_id']
                log('start_task %s' % task_id)
                async_start_task(constellation, task_id)

            elif cmd == 'stop_task':
                constellation = data['constellation']
                async_stop_task(constellation)

        except Exception:
            log("Error processing message [%s]" % msg)
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)


if __name__ == "__main__":

    try:
        log("Cloudsim daemon started pid %s" % os.getpid())
        log("args: %s" % sys.argv)

        tick_interval = 5
    
    
        boto_path = '/var/www-cloudsim-auth/boto-useast'
        softlayer_path = '/var/www-cloudsim-auth/softlayer.json'
        root_dir = '/var/www-cloudsim-auth/machines'
        cloudsim_portal_key_path = '/var/www-cloudsim-auth/cloudsim_portal.key'
        cloudsim_portal_json_path = '/var/www-cloudsim-auth/cloudsim_portal.json'
        cloudsim_bitbucket_key_path = '/var/www-cloudsim-auth/cloudsim_bitbucket.key'

        if len(sys.argv) > 1:
            boto_path = os.path.abspath(sys.argv[1])

        if len(sys.argv) > 2:
            softlayer_path = os.path.abspath(sys.argv[2])

        if len(sys.argv) > 3:
            root_dir = os.path.abspath(sys.argv[3])

        if len(sys.argv) > 4:
            cloudsim_portal_key_path = os.path.abspath(sys.argv[4])

        if len(sys.argv) > 5:
            cloudsim_portal_json_path = os.path.abspath(sys.argv[5])

        config = {}
        config['cloudsim_version'] = '1.5.0'
        config['boto_path'] = boto_path
        config['softlayer_path'] = softlayer_path
        config['machines_directory'] = root_dir
        config['cloudsim_portal_key_path'] = cloudsim_portal_key_path
        config['cloudsim_portal_json_path'] = cloudsim_portal_json_path
        config['cloudsim_bitbucket_key_path'] = cloudsim_bitbucket_key_path
        config ['other_users'] = []
        config ['cs_role'] = "admin"
        config ['cs_admin_users'] = []
        
        set_cloudsim_config(config)
        _load_cloudsim_configurations_list()

        run(root_dir, tick_interval)

    except Exception, e:
        log("cloudsimd.py error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
