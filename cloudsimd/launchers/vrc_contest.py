from __future__ import print_function

import unittest
import os
import time
import zipfile
from shutil import copyfile


import redis
import logging

from launch_utils.traffic_shapping import  run_tc_command

import launch_utils.softlayer

from launch_utils.monitoring import update_machine_aws_states, constellation_is_terminated,\
    monitor_launch_state, monitor_simulator, monitor_cloudsim_ping,\
    get_ssh_client
import shutil
from launch_utils.softlayer import load_osrf_creds, reload_servers,\
    get_softlayer_path, wait_for_server_reloads, get_machine_login_info,\
    setup_ssh_key_access, create_ssh_key
from launch_utils.launch_db import get_constellation_data, ConstellationState
from launch_utils import sshclient
from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.launch import get_unique_short_name
from launch_utils.startup_scripts import get_vpc_router_script, get_vpc_open_vpn,\
    get_drc_startup_script
from launch_utils.sshclient import SshClient, clean_local_ssh_key_entry
from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue



ROUTER_IP='10.0.0.50'
SIM_IP='10.0.0.51'
FC1_IP='10.0.0.52'
FC2_IP='10.0.0.53'
OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'
    
def log(msg, channel = "vrc_contest"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("vrc_contest log> %s" % msg)


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



    
    
launch_sequence = ["nothing", "os_reload", "init_router", "init_privates", "startup", "configure", "reboot", "running"]    

class ReloadOsCallBack(object):
    def __init__(self, constellation_name, machines_dict):
        self.constellation_name = constellation_name
        self.machines_dict = machines_dict
        self.constellation_state = ConstellationState(constellation_name)
    
    def callback(self, machine_name, state):
        msg_key = self.machines_dict[machine_name]
        log( "[%s] %s [%s] %s" % (self.constellation_name, machine_name, msg_key, state))
        self.constellation_state.set_value(msg_key, state)
    
    
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
    
    constellation.set_value("fc1_ip", "xxx")
    constellation.set_value("fc2_ip", "xxx")
    constellation.set_value("sim_ip", "xxx")

    constellation.set_value('fc1_launch_msg', 'nothing')
    constellation.set_value('fc2_launch_msg', 'nothing')
    constellation.set_value('simulation_launch_msg', 'nothing')


    constellation.set_value("fc1_aws_id", "xxx")
    constellation.set_value("fc2_aws_id", "xxx")
    constellation.set_value("simulation_aws_id", "xxx")
    constellation.set_value("router_aws_id", "xxx")
    
    machine_names_prefix = ('router','sim' , 'fc2', 'fc1')
    init_computer_data(constellation_name, machine_names_prefix)

    constellation.set_value("error", "")
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    

    # compute the softlayer machine names
    machine_names = [x + "-" + constellation_prefix for x in  machine_names_prefix]
    reload_servers(osrf_creds, machine_names)
    
    constellation.set_value("launch_stage", "os_reload")    
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")


def add_ubuntu_user_to_router(router_ip, password, constellation_directory):
    clean_local_ssh_key_entry(router_ip)
    create_ssh_key('key-router', constellation_directory)
    # setup a ubuntu sudoer no password user with an ssh key
    router_pub_key_path = os.path.join(constellation_directory, "key-router.pem.pub"  )
    setup_ssh_key_access(router_ip, password, router_pub_key_path)
    router_priv_key_path = os.path.join(constellation_directory, "key-router.pem"  )
    log ("ssh -i %s ubuntu@%s" % (router_priv_key_path, router_ip))    


def upload_user_scripts_to_router(router_ip, constellation_directory, sim_ip, fc1_ip, fc2_ip):

    softlayer_scripts_dir = os.path.join( os.path.dirname(launch_utils.softlayer.__file__), 'bash')
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    # create a cloudsim directory on the router
    ssh_router.cmd("mkdir -p cloudsim")
    
    local_fname = os.path.join( softlayer_scripts_dir, 'router_init.bash')
    remote_fname = 'cloudsim/router_init.bash'
    ssh_router.upload_file(local_fname,remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    # run the script
    ssh_router.cmd("cd cloudsim; ./router_init.bash /home/ubuntu/cloudsim %s %s %s" % (sim_ip, fc1_ip, fc2_ip))
    
    # upload ubuntu user setup scripts
    local_fname = os.path.join( softlayer_scripts_dir, 'auto_ubuntu.bash')
    remote_fname = 'cloudsim/auto_ubuntu.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join( softlayer_scripts_dir, 'create_ubuntu_user.exp')
    remote_fname = 'cloudsim/create_ubuntu_user.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    
    local_fname = os.path.join( softlayer_scripts_dir, 'upload_key.exp')
    remote_fname = 'cloudsim/upload_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    
    local_fname = os.path.join( softlayer_scripts_dir, 'process_remote_ssh_key.exp')
    remote_fname = 'cloudsim/process_remote_ssh_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))


def add_ubuntu_user_via_router(router_ip, constellation_directory, machine_prefix, machine_ip, machine_password):
    
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    
    # create keys for machine
    create_ssh_key("key-%s" % machine_prefix, constellation_directory)
    
    # upload public key to router
    local_fname = os.path.join(constellation_directory, 'key-%s.pem.pub' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem.pub' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload public key %s to %s" % (local_fname, remote_fname))
        
    # upload private key to router
    local_fname = os.path.join(constellation_directory, 'key-%s.pem' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload private key %s to %s" % (local_fname, remote_fname))
    # execute script on router
    cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-%s.pem.pub" % (machine_ip, machine_password, machine_prefix)
    log(cmd)
    ssh_router.cmd(cmd)
    

def initialize_router(constellation_name, constellation_prefix, osrf_creds_fname, constellation_directory):
    
    constellation = ConstellationState( constellation_name)
    
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init_router'):
        return
    
    if os.path.exists(constellation_directory):
        shutil.rmtree(constellation_directory)
    os.makedirs(constellation_directory)

    machines_dict = {'sim-%s' % constellation_prefix:'simulation_launch_msg',
                     'router-%s' % constellation_prefix:'router_launch_msg', 
                     'fc2-%s' % constellation_prefix:'fc2_launch_msg', 
                     'fc1-%s' % constellation_prefix:'fc1_launch_msg',
                    }
    
    osrf_creds = load_osrf_creds(osrf_creds_fname)    
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
    wait_for_server_reloads(osrf_creds, machines_dict.keys(), reload_monitor.callback)

    router_name = "router-%s" % constellation_prefix
    
    router_ip, priv_ip, password = get_machine_login_info(osrf_creds, router_name) 
    constellation.set_value("router_public_ip", router_ip )
    
    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(osrf_creds, "sim-%s" % constellation_prefix)
    fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(osrf_creds, "fc1-%s" % constellation_prefix)
    fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(osrf_creds, "fc2-%s" % constellation_prefix)
    
    
    log("ubuntu user setup for machine router %s [%s / %s] " % (router_name, router_ip, priv_ip) )
    # dst_dir = os.path.abspath('.')
    
    log("router %s %s : %s" % (router_name, router_ip, password))
    add_ubuntu_user_to_router(router_ip, password, constellation_directory)
    
    
    upload_user_scripts_to_router(router_ip, constellation_directory, sim_priv_ip, fc1_priv_ip, fc2_priv_ip)
    # avoid ssh error because our server has changed
    constellation.set_value("launch_stage", "init_router")


    
    
def initialize_private_machines(constellation_name, constellation_prefix, drcsim_package_name, credentials_softlayer, constellation_directory):
    
    def provision_ssh_router(router_ip, startup_script, constellation_directory):
        ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
        local_fname = os.path.join(constellation_directory, 'router_startup.bash')
        with open(local_fname, 'w') as f:
            f.write(startup_script)
        remote_fname = 'cloudsim/router_startup_script.bash'
        ssh_router.upload_file(local_fname, remote_fname)
        log("upload %s to %s" % (local_fname, remote_fname))
    
    def provision_ssh_private_machine(machine_name_prefix, router_ip, private_machine_ip, machine_password, startup_script, constellation_directory ):
    
        add_ubuntu_user_via_router(router_ip, constellation_directory, machine_name_prefix, private_machine_ip, machine_password)
        ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
        
        local_fname = os.path.join(constellation_directory, '%s_startup.bash' % machine_name_prefix)
        with open(local_fname, 'w') as f:
            f.write(startup_script)
        remote_fname = 'cloudsim/%s_startup_script.bash' % machine_name_prefix
        # send startup script to router
        ssh_router.upload_file(local_fname, remote_fname)
        
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init_privates'):
        return

    router_ip = constellation.get_value("router_public_ip" )
    router_script = get_router_script()
    provision_ssh_router(router_ip, router_script, constellation_directory)
    
    osrf_creds = load_osrf_creds(credentials_softlayer)

    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(osrf_creds, "sim-%s" % constellation_prefix)
    sim_script = get_sim_script(drcsim_package_name)
    log("provision sim [%s / %s] %s" % (sim_pub_ip, sim_priv_ip, sim_root_password))
    provision_ssh_private_machine("sim", router_ip, sim_priv_ip, sim_root_password, sim_script, constellation_directory)

    fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(osrf_creds, "fc1-%s" % constellation_prefix)
    fc1_script = get_fc1_script(drcsim_package_name)
    log("provision fc1 [%s / %s] %s" % (fc1_pub_ip, fc1_priv_ip, fc1_root_password))
    provision_ssh_private_machine("fc1", router_ip, fc1_priv_ip, fc1_root_password, fc1_script, constellation_directory)

    fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(osrf_creds, "fc2-%s" % constellation_prefix)
    fc2_script = get_fc2_script(drcsim_package_name)
    log("provision fc2 [%s / %s] %s" % (fc2_pub_ip, fc2_priv_ip, fc2_root_password))
    provision_ssh_private_machine("fc2", router_ip, fc2_priv_ip, fc2_root_password, fc2_script, constellation_directory)

    log('configure_machines done')    
    constellation.set_value("launch_stage", "init_privates")

def startup_scripts(constellation_name):
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value('constellation_directory')

    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)    

    ssh_router.cmd("cloudsim/fc1_init.bash")
    ssh_router.cmd("cloudsim/fc2_init.bash")
    ssh_router.cmd("cloudsim/sim_init.bash")

    constellation.set_value("launch_stage", "startup")
    
def configure_ssh(constellation_name, constellation_directory):

    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('configure'):
        return

    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)

    constellation.set_value("launch_stage", "configure")    
    
#    roles_to_reservations = {}
#    roles_to_reservations['router_state'] = constellation.get_value('router_aws_reservation_id')
#    roles_to_reservations['sim_state'] = constellation.get_value('sim_aws_reservation_id')
#    roles_to_reservations['field1_state'] = constellation.get_value('field1_aws_reservation_id')
#    roles_to_reservations['field2_state'] = constellation.get_value('field2_aws_reservation_id')
#    
#    # running_instances = wait_for_multiple_machines_instances(ec2conn, roles_to_reservations, constellation, max_retries = 500, final_state = 'network_setup')
#    router_ip_address  = None
#    sim_ip_address = None
#    field1_ip_address = None
#    field2_ip_address = None
    
#    constellation.set_value('router_ip_address', router_ip_address)
#    constellation.set_value('sim_ip_address', sim_ip_address)
#    constellation.set_value('field1_ip_address', field1_ip_address)
#    constellation.set_value('field2_ip_address', field2_ip_address)
    
#    router_tags = {'Name': '%s_router' % constellation_name}
#    router_tags.update(tags)
#    sim_tags = {'Name': '%s_sim' % constellation_name}
#    sim_tags.update(tags)
#    field1_tags = {'Name': '%s_field1' % constellation_name}
#    field1_tags.update(tags)
#    field2_tags = {'Name': '%s_field2' % constellation_name}
#    field2_tags.update(tags)
    
    # Set tags
#    router_key_name = constellation.get_value('router_key_name')
#    router_ssh = SshClient(constellation_directory, router_key_name, 'ubuntu', router_ip_address)
#    
#    sim_key_name = constellation.get_value('sim_key_name')
#    sim_ssh = SshClient(constellation_directory, sim_key_name, 'ubuntu', sim_ip_address)
#    
#    field1_key_name = constellation.get_value('field1_key_name')
#    field1_ssh = SshClient(constellation_directory, field1_key_name, 'ubuntu', field1_ip_address)
#    
#    field2_key_name = constellation.get_value('field2_key_name')
#    field2_ssh = SshClient(constellation_directory, field2_key_name, 'ubuntu', field2_ip_address)
#    
#    router_networking_done = get_ssh_cmd_generator(router_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "router_state", 'packages_setup' ,max_retries = 1000)
#    sim_networking_done = get_ssh_cmd_generator(sim_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "sim_state", 'packages_setup' ,max_retries = 1000)
#    field1_networking_done = get_ssh_cmd_generator(field1_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "field1_state", 'packages_setup' ,max_retries = 1000)
#    field2_networking_done = get_ssh_cmd_generator(field2_ssh,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "field2_state", 'packages_setup' ,max_retries = 1000)
#    empty_ssh_queue([router_networking_done, sim_networking_done, field1_networking_done, field2_networking_done], sleep=2)
#
    


def reboot_machines(constellation_name, constellation_directory):
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'reboot':
        return
    
    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    ssh_router.cmd("cloudsim/reboot_sim.bash")
    ssh_router.cmd("cloudsim/reboot_fc1.bash")
    ssh_router.cmd("cloudsim/reboot_fc2.bash")
           
    constellation.set_value("launch_stage", "reboot")

def run_machines(constellation_name, constellation_directory): 
    constellation = ConstellationState( constellation_name)   
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return
    
    router_ip = constellation.get_value("router_public_ip" )
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
    
    #
    # Wait until machines are online (rebooted?)
    #
    router_done = get_ssh_cmd_generator(ssh_router,"ls cloudsim/setup/done", "cloudsim/setup/done",  constellation, "router_state", "running",  max_retries = 500)
    sim_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "sim_state", "running",  max_retries = 500)
    fc1_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_fc1.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "fc1_state", "running",  max_retries = 500)
    fc2_done    = get_ssh_cmd_generator(ssh_router,"cloudsim/find_file_fc2.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "fc2_state", "running",  max_retries = 500)
    
    empty_ssh_queue([router_done, sim_done, fc1_done, fc2_done], sleep=2)
    constellation.set_value("launch_stage", "running")
    
def launch(username, constellation_name, constellation_prefix, credentials_softlayer, constellation_directory ):

    drc_package = "drcsim"
    constellation = ConstellationState( constellation_name)
    if not constellation.has_value("launch_stage"):
        constellation.set_value("launch_stage", "nothing")
    
    reload_os_machines(constellation_name, constellation_prefix, credentials_softlayer)
    initialize_router(constellation_name, constellation_prefix, credentials_softlayer, constellation_directory)
    initialize_private_machines(constellation_name, constellation_prefix, drc_package, credentials_softlayer, constellation_directory)
    
    startup_scripts(constellation_name)
    
    configure_ssh(constellation_name, constellation_directory)
    reboot_machines(constellation_name, constellation_directory)
    run_machines(constellation_name, constellation_directory)
    
  
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
        
#  wait_for_multiple_machines_to_terminate(ec2conn, 
        
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
        cred = get_softlayer_path()
        
        monitor(user, const, cred, 1)
        
  
class VrcCase(unittest.TestCase):
    
    def atest_startup(self):
        constellation_name = 'test_vrc_contest_toto'
        startup_scripts(constellation_name)
    
    def test_launch(self):
        
        constellation_prefix = "01"
        launch_stage = 'init_privates' # before restart 
        # "os_reload" #  
        # "nothing" 
        
        self.constellation_name = 'test_vrc_contest_%s' % constellation_prefix 
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
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        self.tags = {'TestCase':CONFIGURATION, 'configuration': CONFIGURATION, 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"}
        
        constellation.set_value("launch_stage", launch_stage)
        launch(self.username, self.constellation_name, constellation_prefix, self.credentials_softlayer, self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_softlayer, i)
            time.sleep(1)
        
        terminate(self.constellation_name, self.credentials_softlayer)

    def atest_monitor(self):

        self.constellation_name =  "cxf44f7040"
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer  = get_softlayer_path()

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
    
        
    def Xtest_router_ubuntu(self):
        directory = get_test_path('test_router_ubuntu')
        router_ip = '50.97.149.39'
        password = 'SapRekx3'
        os.makedirs(directory)
        print("add_ubuntu_user_to_router %s %s %s" % (router_ip, password, directory) )
        add_ubuntu_user_to_router(router_ip, password, directory)
        s = "ssh -i %s/key-router.pem ubuntu@%s" % (directory, router_ip)
        print(s)
    
    
    def atest_sim_ubuntu_user(self):
        constellation_directory = get_test_path('test_router_ubuntu')
        router_ip = '50.97.149.39'
        upload_user_scripts_to_router(router_ip, constellation_directory)
               
        machine_ip = '10.41.54.2'
        machine_password = 'MJykvzb9'
        print ("sim: %s %s " % (machine_ip, machine_password))

        add_ubuntu_user_via_router(router_ip, constellation_directory, 'sim', machine_ip, machine_password)    
        
    
    def stest_ubuntu_user_on_sim_from_router(self):
        
        constellation = ConstellationState( 'test_vrc_contest_toto')
        
        constellation_directory = constellation.get_value("constellation_directory")
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu', router_ip)
        credentials_softlayer  = get_softlayer_path()
        osrf_creds = load_osrf_creds(credentials_softlayer)
        
        pub_ip, ip, password = get_machine_login_info(osrf_creds, "sim-01")
        log("setting up ubuntu user on simulator machine [%s / %s]" % (pub_ip,ip))
        cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-sim.pem.pub" % (ip, password)
        log(cmd)
        out = ssh_router.cmd(cmd)
        log(out)


    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        #terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       