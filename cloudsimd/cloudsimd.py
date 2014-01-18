#!/usr/bin/python
from __future__ import print_function

import os
import sys
import time
import multiprocessing
import redis
import json
import logging
import traceback
import datetime
from json import loads

from launchers.launch_utils import get_unique_short_name
from launchers.launch_utils.launch_db import ConstellationState
from launchers.launch_utils.launch_db import get_cloudsim_config
from launchers.launch_utils.launch_db import set_cloudsim_config
from launchers.launch_utils import LaunchException
from launchers.launch_utils.launch_db import get_cloudsim_version
from launchers.launch_utils import get_constellation_names
from launchers.launch_utils.launch_db import set_cloudsim_configuration_list
from launchers.launch_utils.launch_db import log_msg
from launchers.launch_utils.launch_db import init_constellation_data

from launchers.launch_utils.aws import aws_connect

# These imports are here for interactive use (with iPython), not necessarily
# referenced in this code module. 
from launchers.launch_utils.softlayer import load_osrf_creds
from launchers.launch_utils.aws import read_boto_file
import unittest

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
               'starting',
               'running',
               'stopping',
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
            if state not in ['ready']:
                cs.update_task_value(task_id, 'task_state', 'ready')
                cs.update_task_value(task_id, 'task_message',
                                     'Ready to run')


def gather_cs_credentials():
    """
    Gather the names and IP addresses of all CloudSim constellations
    and pretty-print them for handing out to users
    """
    consts = [x for x in list_constellations() if 'configuration' in x \
              and x['configuration'].startswith('CloudSim')]
    for const in consts:
        try:
            print('Your CloudSim information:')
            print('IP address: %s'%(const['simulation_ip']))
            # print('Username: guest')
            # print('Password: %s'%(const['constellation_name']))
            print('\n\n\n')
        except Exception as e:
            print('Failed to get information for constellation %s: %s'%(const,
                                                                        e))

    
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
    def __init__(self, launch, 
                 terminate, 
                 update, 
                 monitor, 
                 start_task,
                 stop_task,
                 start_gzweb_server,
                 stop_gzweb_server):
        self.launch = launch
        self.terminate = terminate
        self.update = update
        self.monitor = monitor
        self.start_task = start_task
        self.stop_task = stop_task
        self.start_gzweb = start_gzweb_server
        self.stop_gzweb = stop_gzweb_server


def get_plugin(configuration):
    """
    Each type of constellation has a plugin that implements the details of
    launch-terminate and start-stop simulation.
    This is the switch.
    """
    plugin = None
    #log("get_plugin '%s'" % configuration)

    if configuration.startswith("CloudSim"):
        from launchers import cloudsim as c
        plugin = ConstellationPlugin(c.launch, 
                                     c.terminate,
                                     c.update,
                                     c.monitor,
                              None, None, None, None)

    elif configuration.startswith('DRC'):
        from launchers import vrc_contest as c
        plugin = ConstellationPlugin(c.launch,
                                     c.terminate,
                                     c.update,
                                     c.monitor,
                                     c.start_task,
                                     c.stop_task,
                                     c.start_gzweb,
                                     c.stop_gzweb)
    
    elif configuration.startswith('Simulator'):
        from launchers import simulator as c
        plugin = ConstellationPlugin(c.launch,
                                     c.terminate,
                                     c.update,
                                     c.monitor,
                                     c.start_task,
                                     c.stop_task,
                                     c.start_gzweb,
                                     c.stop_gzweb)

    else:
        raise UnknownConfig('Invalid configuration "%s"' % (configuration,))
    
    log("get_plugin: [%s] %s" % (configuration, plugin))
    return plugin

ROUTER_IP = '10.0.0.50'
SIM_IP = '10.0.0.51'
FC1_IP = '10.0.0.52'
FC2_IP = '10.0.0.53'
OPENVPN_SERVER_IP = '11.8.0.1'
OPENVPN_CLIENT_IP = '11.8.0.2'
def config_derscription_vrc(cloud_provider, region):
    
    def _get_config(config_name, config_description, router_ami, sim_ami):
        has_fc1 = False
        has_fc2 = False
        router_public_network_itf = "eth0"
        router_private_network_itf = None
#         if cloud_provider == "softlayer":
#             router_public_network_itf = "bond1"
#             router_private_network_itf = "bond0"
        openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP)  # '11.8.0.2'
        private_subnet = '10.0.0.0/24'
        machines = {}
        machines['router'] = {'hardware': 'm1.large',    # 't1.micro',
                      'software': router_ami,
                      'ip': ROUTER_IP,   # 'startup_script': router_script,
                      'public_network_itf': router_public_network_itf,
                      'private_network_itf': router_private_network_itf,
                      'security_group': [{'name': 'openvpn',
                                          'protocol': 'udp',
                                          'from_port': 1194,
                                          'to_port': 1194,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ping',
                                           'protocol': 'icmp',
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ssh',
                                           'protocol': 'tcp',
                                          'from_port': 22,   # ssh
                                          'to_port': 22,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'all udp on private sub',
                                           'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                          {'name': 'all tcp on private sub',
                                          'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                         {'name': 'gzweb',
                                          'protocol': 'tcp',
                                          'from_port': 8080,
                                          'to_port': 8080,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'gzweb websocket',
                                          'protocol': 'tcp',
                                          'from_port': 7681,
                                          'to_port': 7681,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'python notebook',
                                          'protocol': 'tcp',
                                          'from_port': 8888,
                                          'to_port': 8888,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'robot web tools',
                                          'protocol': 'tcp',
                                          'from_port': 9090,
                                          'to_port': 9090,
                                          'cidr': '0.0.0.0/0', },
                                         ]}
        machines['sim'] = {'hardware': 'cg1.4xlarge',
                  'software': sim_ami,
                  'ip': SIM_IP,
                      'security_group': [{'protocol': 'icmp',  # ping
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                         {'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                         {'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                         {'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, },
                                         {'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, }]
                    }

        if has_fc1:
            machines['fc1'] = {'hardware': 'cg1.4xlarge',
                      'software': 'ubuntu_1204_x64_cluster',
                      'ip': FC1_IP,
                        }
        if has_fc2:
            machines['fc2'] = {'hardware': 'cg1.4xlarge',
                      'software': 'ubuntu_1204_x64_cluster',
                      'ip': FC2_IP,
                        }
        
        config = {"name": config_name,
                  "description": config_description,
                  "machines" : machines
                  }
        return config
    
    configurations = []
    vrc_desc = """DRC Atlas simulator: a router and a GPU simulator, using gazebo and drcsim packages
<ol>
  <li>Hardware:
      <ol>
          <li>Router: m1.large (large server)</li>
          <li>Simulator: cg1.4xlarge (Single tenant GPU cluster instance)</li>
      </ol>
  </li>
  <li>OS: Ubuntu 12.04 (Precise)</li>
  <li>ROS: Groovy</li>
  <li>Simulator: Gazebo (current)</li>
  <li>Robot: drcsim (Atlas, Darpa Robotics Challenge edition)</li>
</ol>
"""
    stable = "This is a stable version running from saved disk images"
    stable += " that contain preinstalled software."
    
    install = "All software will be downloaded and installed while you wait, "
    install += "from basic OS images, using current software packages."
    
    ubuntu_ami_router = None
    stable_ami_router = None
    ubuntu_ami_sim = None
    stable_ami_sim = None

    if region == "us-east-1":
        ubuntu_ami_router = 'ami-137bcf7a' 
        stable_ami_router = 'ami-8d0155e4' 
        ubuntu_ami_sim = 'ami-98fa58f1' 
        stable_ami_sim = 'ami-8f0155e6'
            
    if region == "eu-west-1":
        ubuntu_ami_router = 'ami-f2191786'
        stable_ami_router = 'ami-bcd235cb' 
        ubuntu_ami_sim = 'ami-fc191788'
        stable_ami_sim = 'ami-bad235cd'        
    
    configurations = []
    if ubuntu_ami_router:
        vrc = _get_config(config_name="VRC (Virtual Robotics Challenge)",
                          config_description=vrc_desc+install,
                          router_ami=ubuntu_ami_router,
                          sim_ami=ubuntu_ami_sim)
    if stable_ami_router:
        vrc_stable = _get_config(config_name="VRC-stable (Virtual Robotics Challenge)",
                          config_description=vrc_desc+install,
                          router_ami=stable_ami_router,
                          sim_ami=stable_ami_sim)
        configurations = [vrc, vrc_stable]
    return configurations

OPENVPN_CLIENT_IP = '11.8.0.2'
def config_derscription_sim(cloud_provider, region):
    
    def _get_config(config_name, config_description, hardware, image_key):
        openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP)  # '11.8.0.2'
        config = {
                 "name": config_name,
                 "description": config_description, 
                 'machines': {'sim' : {'hardware':  hardware,  # 'cg1.4xlarge'  'g2.2xlarge'
                      'software': image_key,
                      'ip': "127.0.0.1",
                      'security_group': [{'name': 'openvpn',
                                          'protocol': 'udp',
                                          'from_port': 1194,
                                          'to_port': 1194,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ping',
                                           'protocol': 'icmp',
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ssh',
                                           'protocol': 'tcp',
                                          'from_port': 22,
                                          'to_port': 22,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'gzweb',
                                          'protocol': 'tcp',
                                          'from_port': 8080,
                                          'to_port': 8080,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'gzweb websocket',
                                          'protocol': 'tcp',
                                          'from_port': 7681,
                                          'to_port': 7681,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'python notebook',
                                          'protocol': 'tcp',
                                          'from_port': 8888,
                                          'to_port': 8888,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'robot web tools',
                                          'protocol': 'tcp',
                                          'from_port': 9090,
                                          'to_port': 9090,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'all tcp on vpn',
                                          'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, },
                                         {'name': 'all udp on vpn',
                                          'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, }
                                         ]}}}
        return config
   

    sim_g1_description = """DRC Atlas simulator: GPU simulator using gazebo and drcsim packages
<ol>
  <li>Hardware:
      <ol>
          <li>Simulator machine type: cg1.4xlarge</li>
      </ol>
  </li>
  <li>OS: Ubuntu 12.04 (Precise)</li>
  <li>ROS: Groovy</li>
  <li>Simulator: Gazebo (current)</li>
  <li>Robot: drcsim (Atlas, Darpa Robotics Challenge edition)</li>
</ol>
"""
    stable = "This is a stable version running from saved disk images"
    stable += " that contain preinstalled software."
    
    install = "All software will be downloaded and installed while you wait, "
    install += "from basic OS images, using current software packages."

    configurations = [] 
    if cloud_provider != "Amazon Web Services":
        return configurations

    ubuntu_ami_g1 = None
    stable_ami_g1 = None
    
    hardware = 'cg1.4xlarge'
    
    if region == "us-east-1":
        ubuntu_ami_g1 = 'ami-98fa58f1'
        stable_ami_g1 = 'ami-8f0155e6'
    if region == "eu-west-1":
        ubuntu_ami_g1 = 'ami-fc191788'
        stable_ami_g1 = 'ami-dd3fd2aa'
    
    if ubuntu_ami_g1:
        sim_cg1 = _get_config(config_name="Simulator-stable (cg1.4xlarge)",
                              config_description=sim_g1_description + install,
                              hardware='cg1.4xlarge',
                              image_key=ubuntu_ami_g1)
        
        sim_cg1_stable = _get_config(config_name="Simulator-stable (cg1.4xlarge)",
                              config_description=sim_g1_description + stable,
                              hardware='cg1.4xlarge',
                              image_key=stable_ami_g1)       
        configurations = [sim_cg1, sim_cg1_stable]
    return configurations
    
def config_derscription_cs(cloud_provider, region):

    def _get_config(config_name, config_description, image_key):
            config  = {
        "name": config_name,
        "description": config_description,
        "machines":{
            "cs":{'hardware': 'm1.small',
              'ip': "127.0.0.1",
              'software': image_key,
              'security_group': [{'name': 'ping',
                                   'protocol': 'icmp',
                                  'from_port': -1,
                                  'to_port': -1,
                                  'cidr': '0.0.0.0/0', },
                                  {'name': 'ssh',
                                   'protocol': 'tcp',
                                  'from_port': 22,
                                  'to_port': 22,
                                  'cidr': '0.0.0.0/0', },
                                  {'name': 'http',
                                  'protocol': 'tcp',
                                  'from_port': 80,
                                  'to_port':80,
                                  'cidr': '0.0.0.0/0', }, ]}}}
            return config

    cloudsim_description = """CloudSim Web App running in the Cloud
<ol>
  <li>Hardware: micro</li>
  <li>OS: Ubuntu 12.04 (Precise)</li>
  <li>Web server: Apache</li>
</ol>
"""

    stable = "This is a stable version running from saved disk images"
    stable += " that contain preinstalled software."
    
    install = "All software will be downloaded and installed while you wait, "
    install += "from basic OS images, using current software packages."

    configurations = []
    if cloud_provider != "Amazon Web Services":
        return configurations

    ubuntu_ami = None
    stable_ami = None
    
    if region == "us-east-1":
        ubuntu_ami = 'ami-137bcf7a'
        stable_ami = 'ami-f55f7b9c'
    if region == "eu-west-1":
        ubuntu_ami = 'ami-f2191786'
        stable_ami = 'ami-0f3ed378'
    if region == "us-west-2":
        ubuntu_ami = 'ami-52b22962'
        stable_ami = None


    if ubuntu_ami:
        config_name = "CloudSim (m1.small)"
        config_description = cloudsim_description + install
        
        config = _get_config("CloudSim (m1.small)",
                             cloudsim_description + install,
                             ubuntu_ami)
    if stable_ami:      
        config_stable = _get_config("CloudSim-stable (m1.small)",
                                    config_description + stable,
                                    stable_ami)
        configurations = [config, config_stable]
    return configurations


def _get_all_configurations():

    regions = ["US East (N. Virginia)", "EU (Ireland)", "US West (Oregon)"]
    configs = {}

    configs["aws"] = {"description": "Amazon Web Services",
             "regions": {
                         "us-east-1" : {"description":"US East (N. Virginia)",
                                        "configurations": []},
                         "eu-west-1" : {"description":"EU (Ireland)",
                                        "configurations": []},
                         "us-west-2" : {"description":"US West (Oregon)",
                                        "configurations": []},                         
                         }
                }

    for region in ["us-east-1", "eu-west-1", "us-west-2"]:
        config_list = configs["aws"]["regions"][region]["configurations"]
        config_list += config_derscription_sim("aws", region)
        config_list += config_derscription_cs("aws", region)
        config_list += config_derscription_vrc("aws", region)
        
    configs["OpenStack"] = {"description": "OpenStack",
                            "regions": {"nova": {"description":"N/A", 
                                                 "configurations": []}
                                        }}
    return configs


def _load_cloudsim_configurations_list():
    """
    Loads the available configurations depending on the credentials. 
     - AWS constellations if AWS credentials are available
     - A list of constellations for SoftLayer credentials
     This function is called upon CloudSim startup, and as a redis command
     (After credentials are overwritten by the web app, for example)
    """
    configs = _get_all_configurations()                                  
    set_cloudsim_configuration_list(configs)

def launch_cmd(root_dir, data):
    constellation_name = "c" + get_unique_short_name()
    constellation = ConstellationState(constellation_name)
    # put the minimum information in Redis so that the monitoring can work
    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('configuration', data['configuration'])
    
    async_launch(constellation_name, data)
    async_monitor(constellation_name)


def launch(constellation_name, data):
    """
    Deploys a constellation. The configuration determines what type of
    constellation will be launched. the constellation directory is where all
    data should be saved (ssh keys, downloadable scripts, etc.)
    """
    proc = multiprocessing.current_process().name
    log("LAUNCH [%s] from proc %s" % (constellation_name, proc))
    constellation = ConstellationState(constellation_name)
    try:
        config = data['configuration']
        cloudsim_config = get_cloudsim_config()
        log("preparing REDIS and filesystem %s" % constellation_name)
        init_constellation_data(constellation_name, data, cloudsim_config)
        constellation_plugin = get_plugin(config)

        constellation.set_value('constellation_state', 'launching')
        log("calling the plugin's launch function")
        constellation_plugin.launch(constellation_name, data)
        constellation.set_value('constellation_state', 'running')
        
        log("Launch of constellation %s done" % constellation_name)
    except Exception, e:
        tb = traceback.format_exc()
        constellation.set_value('error', 'Launch aborted with exception: '
                                '%s<pre>%s</pre>' % (e,tb))
        log("LAUNCH ERROR traceback:  %s" % tb)


def update_constellation(constellation_name):
    """
    Updates the constellation via the cloud interface. 
    This is an operation applied to a running constellation to ugrade the
    software
    """
    proc = multiprocessing.current_process().name
    log("update '%s' from proc '%s'" % (constellation_name, proc))
    constellation = ConstellationState(constellation_name)
    try:
        config = constellation.get_value('configuration')
        constellation_plugin = get_plugin(config)
        constellation.set_value('constellation_state', 'updating')
        constellation_plugin.update(constellation_name)
        constellation.set_value('constellation_state', 'running')
    except:
        tb = traceback.format_exc()
        log("UPDATE ERROR traceback:  %s" % tb)


def start_gzweb(constellation_name):
    """
    Starts the gzweb server
    """
    proc = multiprocessing.current_process().name
    log("start_gzweb '%s' from proc '%s'" % (constellation_name,  proc))
    constellation = ConstellationState(constellation_name)
    try:
        config = constellation.get_value('configuration')
        constellation_plugin = get_plugin(config)
        constellation.set_value("gzweb", 'starting')
        constellation_plugin.start_gzweb(constellation_name)
    except:
        tb = traceback.format_exc()
        log("START_GZWEB ERROR traceback:  %s" % tb)


def stop_gzweb(constellation_name):
    """
    Stops the gzweb server 
    """
    proc = multiprocessing.current_process().name
    log("stop_gzweb '%s' from proc '%s'" % (constellation_name,  proc))
    constellation = ConstellationState(constellation_name)
    try:
        config = constellation.get_value('configuration')
        constellation_plugin = get_plugin(config)
        constellation.set_value("gzweb", 'stopping')
        constellation_plugin.stop_gzweb(constellation_name)
    except:
        tb = traceback.format_exc()
        log("STOP_GZWEB ERROR traceback:  %s" % tb)

             
def terminate(constellation_name):
    """
    Terminates the constellation via the cloud interface.
    This could give the resources back to the cloud provider (AWS), 
    or wipe data.
    """
    proc = multiprocessing.current_process().name
    log("terminate '%s' from proc '%s'" % (constellation_name,  proc))

    constellation = ConstellationState(constellation_name)
    try:
        # clear the error message
        constellation.set_value('error', '')
        config = constellation.get_value('configuration')
        log("    configuration is '%s'" % (config))
        constellation_plugin = get_plugin(config)
        constellation.set_value('constellation_state', 'terminating')
        constellation_plugin.terminate(constellation_name)
        constellation.set_value('constellation_state', 'terminated')
    except Exception, e:
        tb = traceback.format_exc()
        constellation.set_value('error', 'Terminate aborted with exception: '
                                '%s<pre>%s</pre>' % (e,tb))
        log("TERMINATE ERROR traceback:  %s" % tb)
            
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
    Starts a simulation task on a constellation. 
    Only one task can run at a time.
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
                cs.update_task_value(task_id, 'task_message', '')
                cs.update_task_value(task_id, 'task_state', 'starting')
                cs.update_task_value(task_id, 
                                     'start_time',
                                     datetime.datetime.utcnow().isoformat())
                # no other task running, and task is ready
                try:
                    constellation_plugin.start_task(constellation_name, task)
                except Exception, e:
                    log("Start task error %s" % e)
                    tb = traceback.format_exc()
                    log("traceback:  %s" % tb)
                    cs.update_task_value(task_id,
                                         'task_message',
                                         'Task failed to start: %s'%(e))
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
                log("can't run task %s while tasks %s "
                        "is already running" % (task_id, current_task))
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
                cs.update_task_value(task_id, 'stop_time',
                                     datetime.datetime.utcnow().isoformat())
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
                log('stop_taks error: wrong state '
                    '"%s" for task "%s" ' % (task['task_state'], task_id))
        else:
            log('stop_task error: no current task')
    except Exception, e:
        log("stop_task error %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


def monitor(constellation_name):
    """
    Loop that monitors the execution of a constellation
    """
    try:
        proc = multiprocessing.current_process().name
        log("monitoring [%s] from proc '%s'" % (constellation_name, proc))

        constellation = ConstellationState(constellation_name)
        config = constellation.get_value('configuration')
        constellation_plugin = get_plugin(config)

        counter = 0
        done = False
        while not done:
            try:
                log("monitor %s (%s)" % (constellation_name, counter))
                done = constellation_plugin.monitor(constellation_name,
                                                    counter)
                log("monitor [%s] returned %s" % (constellation_name, done))
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


def async_monitor(constellation_name):

    try:
        log("cloudsimd async_monitor %s" % (constellation_name))
        p = multiprocessing.Process(target=monitor, 
                                    args=(constellation_name,))
        p.start()
    except Exception, e:
        log("cloudsimd async_monitor Error %s" % e)


def async_launch(constellation_name, data):
    log("cloudsimd async_launch '%s'  %s" % (constellation_name, data))
    try:
        p = multiprocessing.Process(target=launch, args=(constellation_name, 
                                                        data))
        p.start()
    except Exception, e:
        log("cloudsimd async_launch Error %s" % e)


def async_update(constellation_name):

    log("async update '%s'" % (constellation_name))
    try:
        p = multiprocessing.Process(target=update_constellation,
                                    args=(constellation_name,))
        p.start()

    except Exception, e:
        log("Cloudsim async_update Error for constellation "
                            "%s :%s" % (constellation_name,e))


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
            log("      resume_monitoring %s" % constellation_name)
            async_monitor(constellation_name)
        except Exception, e:
            log ("MONITOR ERROR %s in constellation : %s" % (e,
                                                        constellation_name))
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)            
            log("deleting %s from redis database" % constellation_name)


def _async_create_task(constellation_name, data):
    log('_async_create_task')

    p = multiprocessing.Process(target=create_task,
                                args=(constellation_name, data))
    p.start()


def _async_update_task(constellation_name, data):
    log('_async_update_task')
    p = multiprocessing.Process(target=update_task,
                                args=(constellation_name, data))
    p.start()


def _async_delete_task(constellation_name, task_id):
    p = multiprocessing.Process(target=delete_task,
                                args=(constellation_name, task_id))
    p.start()


def _async_start_task(constellation_name, task_id):
    p = multiprocessing.Process(target=start_task,
                                args=(constellation_name, task_id))
    p.start()


def _async_stop_task(constellation_name):
    p = multiprocessing.Process(target=stop_task,
                                args=(constellation_name,))
    p.start()


def _async_reset_tasks(constellation_name):
    p = multiprocessing.Process(target=reset_tasks,
                                args=(constellation_name,))
    p.start()


def _async_update_cloudsim_configuration_list():
    p = multiprocessing.Process(target=_load_cloudsim_configurations_list,
                                args=())
    p.start()


def _async_start_gzweb(constellation_name):
    p = multiprocessing.Process(target=start_gzweb,
                                args=(constellation_name,))
    p.start()

    
def _async_stop_gzweb(constellation_name):
    p = multiprocessing.Process(target=stop_gzweb,
                                args=(constellation_name,))
    p.start()

    
def _run_cloudsim_cmd_loop(root_dir, tick_interval):

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
            log("CMD= \"%s\" DATA=\"%s\" " % (cmd, data))

            if cmd == '_load_cloudsim_configurations_list':
                _async_update_cloudsim_configuration_list()

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
                _async_create_task(constellation, data)

            elif cmd == "update_task":
                constellation = data['constellation']
                data.pop('constellation')
                data.pop('command')
                _async_update_task(constellation, data)

            elif cmd == 'delete_task':
                constellation = data['constellation']
                task_id = data['task_id']
                _async_delete_task(constellation, task_id)

            elif cmd == 'start_task':
                log('start_task')
                constellation = data['constellation']
                task_id = data['task_id']
                log('start_task %s' % task_id)
                _async_start_task(constellation, task_id)

            elif cmd == 'stop_task':
                constellation = data['constellation']
                _async_stop_task(constellation)
            
            elif cmd == 'reset_tasks':
                constellation = data['constellation']
                _async_reset_tasks(constellation)
            
            # gzweb commands
            elif cmd == 'start_gzweb':
                constellation = data['constellation']
                _async_start_gzweb(constellation)

            elif cmd == 'stop_gzweb':
                constellation = data['constellation']
                _async_stop_gzweb(constellation)

        except Exception:
            log("Error processing message [%s]" % msg)
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)


class Configs_test(unittest.TestCase):
    
    def test(self):
        import pprint
        configs = _get_all_configurations()
        pp = pprint.PrettyPrinter(indent=4)
        pp.pprint(configs)

if __name__ == "__main__":
#     from launchers.launch_utils.testing import get_test_runner
#     xmlTestRunner = get_test_runner()
#     unittest.main(testRunner=xmlTestRunner)
    try:
        log("Cloudsim daemon started pid %s" % os.getpid())
        log("args: %s" % sys.argv)
 
        tick_interval = 5
     
        boto_path = '/var/www-cloudsim-auth/boto.ini'
        softlayer_path = '/var/www-cloudsim-auth/softlayer.json'
        root_dir = '/var/www-cloudsim-auth/machines'
        cloudsim_portal_key_path = ('/var/www-cloudsim-auth/' 
                                    'cloudsim_portal.key')
        cloudsim_portal_json_path = ('/var/www-cloudsim-auth/'
                                     'cloudsim_portal.json')
        cloudsim_bitbucket_key_path = ('/var/www-cloudsim-auth/'
                                       'cloudsim_bitbucket.key')
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
        config['cloudsim_version'] = get_cloudsim_version()
        config['boto_path'] = boto_path
        config['softlayer_path'] = softlayer_path
        config['machines_directory'] = root_dir
        config['cloudsim_portal_key_path'] = cloudsim_portal_key_path
        config['cloudsim_portal_json_path'] = cloudsim_portal_json_path
        config['cloudsim_bitbucket_key_path'] = cloudsim_bitbucket_key_path
        config ['other_users'] = []
        config ['cs_role'] = "admin"
        config ['cs_admin_users'] = []
        # openstack
        config['openstack'] ={'username' : 'admin',
                              'api_key' : 'cloudsim',
                              'auth_url' : 'http://172.16.0.201:5000/v2.0',
                              'project_id' : 'admin',
                              'service_type' : 'compute'}
        set_cloudsim_config(config)
        _load_cloudsim_configurations_list()
 
        _run_cloudsim_cmd_loop(root_dir, tick_interval)
 
    except Exception, e:
        log("cloudsimd.py error: %s" % e)
        tb = traceback.format_exc()
        log("traceback:  %s" % tb)


