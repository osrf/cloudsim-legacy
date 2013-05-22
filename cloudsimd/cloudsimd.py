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

from launchers.launch_utils import SshClient

#from common import Machine

from launchers.launch_utils import get_unique_short_name
from launchers.launch_utils.launch_db import ConstellationState
from launchers.launch_utils.launch_db import get_cloudsim_config, set_cloudsim_config


import traceback


from launchers.launch_utils import get_constellation_names
from launchers.launch_utils import get_constellation_data
from launchers.launch_utils import set_constellation_data
from launchers.launch_utils.launch import aws_connect
from launchers.launch_utils.softlayer import get_constellation_prefixes
from launchers.launch_utils.launch_db import set_cloudsim_configuration_list
from launchers.launch_utils.launch import LaunchException


from launchers.launch_utils.softlayer import load_osrf_creds
from launchers.launch_utils.softlayer import softlayer_dash_board
from launchers.launch_utils.softlayer import softlayer_server_scan
import datetime


def log(msg, chan="cloudsimd"):
    try:

        print ("LOG: %s" % msg)
        red = redis.Redis()
        red.publish(chan, msg)
    except Exception:
        pass


class UnknownConfig(LaunchException):
    pass


def launch_constellation(username, configuration, args=None, count=1):
    """
    Launches one (or count) constellation of a given configuration
    """
    r = redis.Redis()

    d = {}
    d['username'] = username
    d['command'] = 'launch'
    d['configuration'] = configuration
    if count > 1:
        d['count'] = count
    if args:
        d['args'] = args

    s = json.dumps(d)
    print("LAUNCH constellation... command: %s " % s)
    r.publish('cloudsim_cmds', s)


def terminate_all_constellations():
    r = redis.Redis()

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


class ConstellationPlugin(object):
    """
    The plugins contains the function pointers for each type of constellation
    Don't forget to register new constellations
    """
    def __init__(self, launch, terminate, monitor, start_task, stop_task):
        self.launch = launch
        self.terminate = terminate
        self.monitor = monitor
        self.start_task = start_task
        self.stop_task = stop_task


def get_plugin(configuration):
    """
    Each type of constellation has a plugin that implements the details of
    launch-terminate and start-stop simulation.
    This is the switch.
    """
    plugin = None
    log("get_plugin '%s'" % configuration)

    if configuration == 'AWS CloudSim':
        from launchers import amazon_cloudsim as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, None, None)

    elif configuration == 'AWS simulator':
        from launchers import simulator as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, c.start_task, c.stop_task)

    elif configuration == 'AWS trio':
        from launchers import amazon_trio as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, c.start_task, c.stop_task)

    elif configuration == 'AWS micro trio':
        from launchers import amazon_micro_trio as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, c.start_task, c.stop_task)

    elif configuration.startswith("OSRF VRC Constellation "):
        from launchers import vrc_contest as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, c.start_task, c.stop_task)

    elif configuration.startswith("OSRF CloudSim "):
        from launchers import cloudsim as c
        plugin = ConstellationPlugin(c.launch, c.terminate, c.monitor, None, None)
    else:
        raise UnknownConfig('Invalid configuration "%s"' % (configuration,))
    log("get_plugin: %s %s" % (configuration, plugin))
    return plugin


def update_cloudsim_configuration_list():

    configs = {}
    configs['AWS trio'] = {'description': "3 machines for the VRC competition: a GPU field computer, a router and a GPU simulator, using gazebo and drcsim packages"}
    configs['AWS simulator'] = {'description': "1 machine for using gzserver on the cloud: GPU computer with the latest ros-fuerte, gazebo and drcsim packages installed"}
    configs['AWS CloudSim'] = {'description': "1 machine for starting a CloudSim on the cloud: A micro instance web app clone"}
    #configs['trio AWS (prerelease)'] = {'description': "3 machines for the VRC competition: a GPU field computer, a router and a GPU simulator, using gazebo and drcsim pre-release packages"}
    #configs['vpc_micro_trio'] = {'description': "3 micro instances for testing constellations: field computer, router and simulator"}
    #configs['simulator AWS (prerelease)'] = {'description': "1 machine for using gzserver on the cloud: GPU computer with the latest ros-fuerte, gazebo and drcsim pre-release packages installed"}

    const_prefixes = []
    config = get_cloudsim_config()
    osrf_creds_path = config['softlayer_path']
    try:

        try:
            osrf_creds = load_osrf_creds(osrf_creds_path)
        except Exception, e:
            log("SoftLayer credentials loading error: %s" % e)

        const_prefixes = get_constellation_prefixes(osrf_creds)
        log("softlayer constellations: %s" % const_prefixes)
    except:
        log("No SoftLayer constellations (credentials: %s)" % osrf_creds_path)
        pass

    for prefix in const_prefixes:
        configs['OSRF CloudSim %s' % prefix] = {'description': "DARPA VRC Challenge CloudSim server"}
        configs['OSRF VRC Constellation %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
        configs['OSRF VRC Constellation nightly build %s' % prefix] = {'description': "DARPA VRC Challenge constellation: 1 simulator, 2 field computers and a router"}
    set_cloudsim_configuration_list(configs)
    #log("cloudsim configurations list updated: %s" % configs)


def launch(username,
           config,
           constellation_name,
           args,
           constellation_directory):

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
        constellation.set_value('constellation_state', 'launching')
        constellation.set_value('error', '')

        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        try:
            constellation_plugin.launch(username, config, constellation_name, tags, constellation_directory)
        except Exception, e:
            error_msg = constellation.get_value('error')

            tb = traceback.format_exc()
            log("traceback:  %s" % tb)
            terminate(constellation_name, constellation_directory)
            constellation.set_value('error', '%s' % error_msg)
            constellation.expire(10)
            raise

        log("Launch of constellation %s done" % constellation_name)

    except Exception, e:

        log("cloudsimd.py launch error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def terminate(constellation, constellation_directory):
    """
    Terminates the machine via the cloud interface. Files will be removed by the
    monitoring process
    """

    proc = multiprocessing.current_process().name
    log("terminate '%s' from proc '%s'" % (constellation,  proc))

    try:

        data = get_constellation_data(constellation)
        config = data['configuration']
        log("    configuration is '%s'" % (config))

        constellation_plugin = get_plugin(config)
        constellation_plugin.terminate(constellation, constellation_directory)

    except Exception, e:
        log("cloudsimd.py terminate error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)

    constellation = ConstellationState(constellation)
    constellation.set_value('constellation_state', 'terminated')
    log("Deleting %s from the database" % constellation)
    constellation.expire(1)

task_states = ['ready',
               #'setup',
               'running',
               #'teardown',
               'stopped']


def create_task(constellation_name, data):
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
        log("traceback:  %s" % tb)


def update_task(constellation_name, data):

    #    for k,v in data.iteritems():
    #        log('  %s = %s' % (k,v))
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
        constellation_plugin = get_plugin(config)
        current_task = cs.get_value('current_task')
        if current_task == '':
            task = cs.get_task(task_id)
            task_state = task['task_state']
            if task_state == 'ready':
                cs.set_value('current_task', task_id)
                log('task_state running')
                task['task_state'] = 'running'
                task['start_time'] = datetime.datetime.utcnow().isoformat()
                cs.update_task(task_id, task)
                # no other task running, and task is ready
                try:
                    constellation_plugin.start_task(constellation_name, task)
                except Exception, e:
                    log("Start task error %s" % e)

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
        constellation_plugin = get_plugin(config)

        task_id = cs.get_value('current_task')
        if task_id != '':
            task = cs.get_task(task_id)

            # you can only stop a running task
            if task['task_state'] == 'running':

                task['task_state'] = 'stopping'
                log('task_state stopping')
                task['stop_time'] = datetime.datetime.utcnow().isoformat()
                cs.update_task(task_id, task)
                try:
                    constellation_plugin.stop_task(constellation_name, task)
                except Exception, e:
                    tb = traceback.format_exc()
                    log('task error during stop')
                    log("traceback:  %s" % tb)
                else:
                    log('task stopped successfully')
                finally:
                    task['task_state'] = 'stopped'
                    cs.update_task(task_id, task)
                    cs.set_value('current_task', '')

        else:
            log('stop_task error: no current task')
    except Exception, e:
        log("stop_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def monitor(username, config, constellation_name):

    proc = multiprocessing.current_process().name
    log("monitoring [%s] %s/%s from proc '%s'" % (config, username, constellation_name, proc))
    try:
        done = False
        constellation_plugin = get_plugin(config)
        counter = 0
        while not done:
            try:
                #log("monitor %s (%s)" % (constellation_name, counter) )
                done = constellation_plugin.monitor(username, constellation_name, counter)
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


def async_monitor(username, config, constellation_name):

    log("cloudsimd async_monitor [config %s] %s/%s" % (config, username, constellation_name))
    try:
        p = multiprocessing.Process(target=monitor, args=(username, config, constellation_name))
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


def async_terminate(constellation, constellation_directory):

    log("async terminate '%s'" % (constellation,))
    try:
        p = multiprocessing.Process(target=terminate, args=(constellation,  constellation_directory))
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
            username = constellation['username']
            log("      resume_monitoring config %s" % config)
            log("      resume_monitoring state %s" % state)
            async_monitor(username, config, constellation_name)
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
    p = multiprocessing.Process(target=update_cloudsim_configuration_list,
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
            async_launch(username, config, constellation_name, args, constellation_path)
            async_monitor(username, config, constellation_name)

    elif config.startswith("OSRF"):

        constellation_name = config.replace(" ", "_")
        constellation_path = os.path.join(root_dir, constellation_name)

        if os.path.exists(constellation_path):
            constellation_backup = "%s c%s" % (constellation_name, get_unique_short_name())
            backup_path = os.path.join(root_dir, constellation_backup)
            log("move %s to %s" % (constellation_path, backup_path))
            shutil.move(constellation_path, backup_path)
        os.makedirs(constellation_path)
        async_launch(username, config, constellation_name, args, constellation_path)
        async_monitor(username, config, constellation_name)


def run(root_dir, tick_interval):

    red = redis.Redis()
    ps = red.pubsub()
    ps.subscribe("cloudsim_cmds")

    async_tick_monitor(tick_interval)
    resume_monitoring(root_dir)

    log("CLOUDSIMD STARTED root_dir=%s" % (root_dir))
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

            if cmd == 'update_cloudsim_configuration_list':
                async_update_cloudsim_configuration_list()

            elif cmd == 'launch':
                launch_cmd(root_dir, data)

            elif cmd == 'terminate':
                constellation = data['constellation']
                constellation_path = os.path.join(root_dir, constellation)
                async_terminate(constellation, constellation_path)

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

        set_cloudsim_config(config)
        update_cloudsim_configuration_list()

        run(root_dir, tick_interval)

    except Exception, e:
        log("cloudsimd.py error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)
