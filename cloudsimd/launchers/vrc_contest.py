from __future__ import print_function

import unittest
import os
import time
import zipfile
from shutil import copyfile


import redis
import logging

from launch_utils.traffic_shapping import  run_tc_command

 

from launch_utils.monitoring import update_machine_aws_states, constellation_is_terminated,\
    monitor_launch_state, monitor_simulator, monitor_cloudsim_ping,\
    get_ssh_client
import shutil
from launch_utils.softlayer import load_osrf_creds, reload_servers,\
    get_softlayer_path, wait_for_server_reloads
from launch_utils.launch_db import get_constellation_data, ConstellationState
from launch_utils import sshclient
from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.launch import get_unique_short_name
from launch_utils.startup_scripts import get_vpc_router_script, get_vpc_open_vpn,\
    get_drc_startup_script
from launch_utils.sshclient import SshClient
from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue


FC1_IP='10.0.0.52'
FC2_IP='10.0.0.53'
ROUTER_IP='10.0.0.50'
SIM_IP='10.0.0.51'
OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'
    
def log(msg, channel = "vrc_contest"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)


def get_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)



def start_simulator(constellation, package_name, launch_file_name, launch_args, task_timeout):

    log("1")
    constellation_dict = get_constellation_data(  constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_name    = constellation_dict['sim_key_name']
    log("2")
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    c = "bash cloudsim/start_sim.bash %s %s %s" %(package_name, launch_file_name, launch_args)
    cmd = c.strip()
    ssh_sim = sshclient(sim_machine_dir, sim_key_name, 'ubuntu', sim_ip)
    log("3")
    r = ssh_sim.cmd(cmd)
    log('start_simulator %s' % r)


def stop_simulator(constellation):
    constellation_dict = get_constellation_data( constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_name    = constellation_dict['sim_key_name']
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_sim = SshClient(sim_machine_dir, sim_key_name, 'ubuntu', sim_ip)
    r = ssh_sim.cmd(cmd)
    log('stop_simulator %s' % r)


def start_task(constellation, task):
    
    log("** SIMULATOR *** start_task %s" % task)

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation, 'sim_machine_name', 'sim_key_name', 'simulation_ip', latency, up, down)
    
    log("** START SIMULATOR ***")
    start_simulator(constellation, task['ros_package'], task['ros_launch'], task['ros_args'], task['timeout'])
    
    

        
    
def stop_task(constellation):
    
    log("** SIMULATOR *** STOP TASK %s ***" % constellation)

    latency = 0 
    up = -1
    down = -1
    log("** TC COMMAND ***")
    run_tc_command(constellation, 'sim_machine_name', 'sim_key_name', 'simulation_ip', latency, up, down)
    
    log("** stop simulator ***")
    stop_simulator(constellation)
    

def monitor(username, constellation_name, credentials_ec2, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True
    
    constellation = ConstellationState( constellation_name)
   
    

    update_machine_aws_states(credentials_ec2, constellation_name, {'sim_aws_id':"sim_aws_state",
                                                                    'router_aws_id': 'router_aws_state',
                                                                    'field1_aws_id': 'field1_aws_state',
                                                                    'field2_aws_id': 'field2_aws_state',
                                                                    }) 
    simulation_state = constellation.get_value('sim_state')
    sim_ssh = get_ssh_client(constellation_name, simulation_state,'sim_ip_address', 'sim_key_name' )
    monitor_cloudsim_ping(constellation_name, 'sim_ip_address', 'sim_latency')
    monitor_launch_state(constellation_name, sim_ssh, simulation_state, "tail -1 /var/log/dpkg.log ", 'sim_launch_msg')
    
    monitor_simulator(constellation_name, sim_ssh)
    
    router_state = constellation.get_value('router_state')
    ssh_router = get_ssh_client(constellation_name, router_state,'router_ip_address', 'router_key_name' )
    monitor_cloudsim_ping(constellation_name, 'router_ip_address', 'router_latency')
    monitor_launch_state(constellation_name, ssh_router, router_state, "tail -1 /var/log/dpkg.log", 'router_launch_msg')
    
    field1_state = constellation.get_value('field1_state')
    ssh_field1 = get_ssh_client(constellation_name, field1_state,'field1_ip_address', 'field1_key_name' )
    monitor_cloudsim_ping(constellation_name, 'field1_ip_address', 'field1_latency')
    monitor_launch_state(constellation_name, ssh_field1, field1_state, "tail -1 /var/log/dpkg.log", 'field1_launch_msg')
    
    field2_state = constellation.get_value('field2_state')
    ssh_field2 = get_ssh_client(constellation_name, field2_state,'field2_ip_address', 'field1_key_name' )
    monitor_cloudsim_ping(constellation_name, 'field2_ip_address', 'field2_latency')
    monitor_launch_state(constellation_name, ssh_field2, field2_state, "tail -1 /var/log/dpkg.log", 'field2_launch_msg')
    # log("monitor not done")
    return False





def init_computer_data(constellation_name, prefixes):
    constellation = ConstellationState( constellation_name)
    for prefix in prefixes:
        constellation.set_value('%s_ip_address' % prefix, "nothing")
        constellation.set_value('%s_state' % prefix, "nothing")
        constellation.set_value('%s_aws_state'% prefix, 'nothing')
        constellation.set_value('%s_launch_msg'% prefix, 'starting')
        constellation.set_value('%s_zip_file'% prefix, 'not ready')
        constellation.set_value('%s_latency'% prefix, '[]')
        constellation.set_value('%s_aws_reservation_id'% prefix, 'nothing')
        constellation.set_value('%s_machine_name' % prefix, '%s_%s' % (prefix, constellation_name) )
        constellation.set_value('%s_key_name'% prefix, None)


def get_router_script():
    router_script = get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP, ROUTER_IP, SIM_IP)    
    return router_script

def get_sim_script(drc_package_name):
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, ROUTER_IP)
    sim_script = get_drc_startup_script(open_vpn_script, SIM_IP, drc_package_name)
    return sim_script

def get_fc1_script(drc_package_name):
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, ROUTER_IP)
    field1_script = get_drc_startup_script(open_vpn_script, FC1_IP, drc_package_name)
    return field1_script

def get_fc2_script(drc_package_name):
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, ROUTER_IP)
    field2_script = get_drc_startup_script(open_vpn_script, FC1_IP, drc_package_name)
    return field2_script



    
    
launch_sequence = ["nothing", "os_reload", "startup_script", "configure", "running"]    

class ReloadOsCallBack(object):
    def __init__(self, constellation_name):
        self.constellation_name = constellation_name
    
    def callback(self, machine_name, state):
        log( "[%s] %s %s" % (self.constellation_name, machine_name, state))
    
def reload_os_machines(constellation_name, constellation_prefix, osrf_creds_fname):

    constellation = ConstellationState( constellation_name)
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('os_reload'):
        return
    
    constellation.set_value("constellation_state", "launching")
    constellation.set_value("error", "")
    
    constellation.set_value("configuration_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")
    
    machine_names_prefix = ('router','sim', 'fc1', 'fc2')
    init_computer_data(constellation_name, machine_names_prefix)
 
    constellation.set_value("error", "")
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    

    # compute the softlayer machine names
    machine_names = [x + "-" + constellation_prefix for x in  machine_names_prefix]
    reload_servers(osrf_creds, machine_names)
    
    constellation.set_value("launch_stage", "os_reload")    
    constellation.set_value("setup_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")
    

        
def load_machine_scripts(constellation_name, drc_package, constellation_prefix, osrf_creds_fname, constellation_directory):
    
    constellation = ConstellationState( constellation_name)
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup_script'):
        return
    
    shutil.rmtree(constellation_directory)
    os.makedirs(constellation_directory)

    machine_names_prefix = ('router','sim', 'fc1', 'fc2')   
    machine_names = [x + "-" + constellation_prefix for x in  machine_names_prefix]
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)    
    reload_monitor = ReloadOsCallBack(constellation_name)
    wait_for_server_reloads(osrf_creds, machine_names, reload_monitor.callback)
        
    router_script = get_router_script()
    sim_script = get_sim_script(drc_package)
    fc1_script = get_fc1_script(drc_package)
    fc2_script = get_fc1_script(drc_package)
    
    print(router_script, sim_script, fc1_script,fc2_script )    
    constellation.set_value("launch_stage", "startup_script")
    
def configure_ssh_machines(constellation_name, constellation_prefix, osrf_creds_fname ):
        
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    constellation = ConstellationState( constellation_name)    
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('configure'):
        return
    
    if constellation.get_value("configuration_sequence") == 'done':
        return
    
    constellation_directory = constellation.get_value('constellation_directory')
    
    roles_to_reservations = {}
    roles_to_reservations['router_state'] = constellation.get_value('router_aws_reservation_id')
    roles_to_reservations['sim_state'] = constellation.get_value('sim_aws_reservation_id')
    roles_to_reservations['field1_state'] = constellation.get_value('field1_aws_reservation_id')
    roles_to_reservations['field2_state'] = constellation.get_value('field2_aws_reservation_id')
    
    # running_instances = wait_for_multiple_machines_instances(ec2conn, roles_to_reservations, constellation, max_retries = 500, final_state = 'network_setup')
    router_ip_address  = None
    sim_ip_address = None
    field1_ip_address = None
    field2_ip_address = None
    
    constellation.set_value('router_ip_address', router_ip_address)
    constellation.set_value('sim_ip_address', sim_ip_address)
    constellation.set_value('field1_ip_address', field1_ip_address)
    constellation.set_value('field2_ip_address', field2_ip_address)
    
#    router_tags = {'Name': '%s_router' % constellation_name}
#    router_tags.update(tags)
#    sim_tags = {'Name': '%s_sim' % constellation_name}
#    sim_tags.update(tags)
#    field1_tags = {'Name': '%s_field1' % constellation_name}
#    field1_tags.update(tags)
#    field2_tags = {'Name': '%s_field2' % constellation_name}
#    field2_tags.update(tags)
    
    # Set tags
    router_key_name = constellation.get_value('router_key_name')
    router_ssh = SshClient(constellation_directory, router_key_name, 'ubuntu', router_ip_address)
    
    sim_key_name = constellation.get_value('sim_key_name')
    sim_ssh = SshClient(constellation_directory, sim_key_name, 'ubuntu', sim_ip_address)
    
    field1_key_name = constellation.get_value('field1_key_name')
    field1_ssh = SshClient(constellation_directory, field1_key_name, 'ubuntu', field1_ip_address)
    
    field2_key_name = constellation.get_value('field2_key_name')
    field2_ssh = SshClient(constellation_directory, field2_key_name, 'ubuntu', field2_ip_address)
    
    router_networking_done = get_ssh_cmd_generator(router_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "router_state", 'packages_setup' ,max_retries = 1000)
    sim_networking_done = get_ssh_cmd_generator(sim_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "sim_state", 'packages_setup' ,max_retries = 1000)
    field1_networking_done = get_ssh_cmd_generator(field1_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "field1_state", 'packages_setup' ,max_retries = 1000)
    field2_networking_done = get_ssh_cmd_generator(field2_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "field2_state", 'packages_setup' ,max_retries = 1000)
    empty_ssh_queue([router_networking_done, sim_networking_done, field1_networking_done, field2_networking_done], sleep=2)

    router_done = get_ssh_cmd_generator(router_ssh,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "router_state", "running",  max_retries = 500)
    sim_done = get_ssh_cmd_generator(sim_ssh,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "sim_state", "running",  max_retries = 500)
    field1_done = get_ssh_cmd_generator(field1_ssh,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "field1_state", "running",  max_retries = 500)
    field2_done = get_ssh_cmd_generator(field2_ssh,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "field2_state", "running",  max_retries = 500)
    
    empty_ssh_queue([router_done, sim_done, field1_done, field2_done], sleep=2)
    
    constellation.set_value("launch_stage", "configure")    
    log('configure_machines done')    

def reboot_machines(constellation_name):
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return
    
    constellation.set_value("launch_stage", "running")
    
    
def launch(username, constellation_name, tags, credentials_softlayer, constellation_directory ):
    
    drc_package = "drcsim"
    constellation_prefix = "01"
    constellation = ConstellationState( constellation_name)
    if not constellation.has_value("launch_stage"):
        constellation.set_value("launch_stage", "nothing")
    
    reload_os_machines(constellation_name, constellation_prefix, credentials_softlayer)
    load_machine_scripts(constellation_name, drc_package, constellation_prefix, credentials_softlayer, constellation_directory)
    configure_ssh_machines(constellation_name, constellation_prefix, credentials_softlayer)
    reboot_machines(constellation_name)

    
    
def launch_prerelease(username, constellation_name, tags, credentials_ec2, constellation_directory):
    pass

  
def terminate(constellation_name, osrf_creds_fname):

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    constellation = ConstellationState( constellation_name)
    
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('router_state', 'terminating')
    constellation.set_value('sim_state', 'terminating')
    constellation.set_value('field1_state', 'terminating')
    constellation.set_value('field2_state', 'terminating')
    constellation.set_value('sim_glx_state', "not running")
    
    constellation.set_value('sim_launch_msg', "terminating")
    constellation.set_value('router_launch_msg', "terminating")
    constellation.set_value('field1_launch_msg', "terminating")
    constellation.set_value('field2_launch_msg', "terminating")    
        
#        wait_for_multiple_machines_to_terminate(ec2conn, 
        
    constellation.set_value('sim_state', 'terminated')
    constellation.set_value('sim_launch_msg', "terminated")
    constellation.set_value('router_state', 'terminated')
    constellation.set_value('router_launch_msg', "terminated")
    constellation.set_value('field1_state', 'terminated')
    constellation.set_value('field1_launch_msg', "terminated")
    constellation.set_value('field2_state', 'terminated')
    constellation.set_value('field2_launch_msg', "terminated")

    constellation.set_value('constellation_state', 'terminated')

    



    

class MonitorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxb49a97c4'
        cred = get_boto_path()
        
        monitor(user, const, cred, 1)
        
  
class VrcCase(unittest.TestCase):
    
    
    def atest_monitor(self):
        
        self.constellation_name =  "cxf44f7040"
        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
        
    def test_launch(self):
        
        self.constellation_name = 'test_vrc_contest_7750382e' 
        
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer  = get_softlayer_path()
        
        CONFIGURATION = 'vrc_contest'

        test_name = "test_" + CONFIGURATION
        
        if not self.constellation_name:
            self.constellation_name =  get_unique_short_name(test_name + "_")
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))
        
        constellation = ConstellationState( self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory", self.constellation_directory)
        constellation.set_value("configuration", 'vrc_contest')
        
        constellation.set_value("launch_stage", 'os_reload')
        
        self.tags = {'TestCase':CONFIGURATION, 'configuration': CONFIGURATION, 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"}
        launch(self.username, self.constellation_name, self.tags, self.credentials_softlayer, self.constellation_directory)
                
        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_softlayer, i)
            time.sleep(1)
        
        terminate(self.constellation_name, self.credentials_softlayer)
        
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        #terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       