from __future__ import print_function

import unittest
import os
import time
import zipfile
from shutil import copyfile

import boto
from boto.pyami.config import Config as BotoConfig
import redis
import logging

from launch_utils.traffic_shapping import  run_tc_command

from launch_utils import get_unique_short_name
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance 
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient
from launch_utils import get_ssh_cmd_generator, empty_ssh_queue # task_list
from launch_utils import ConstellationState # launch_db


from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_drc_startup_script,\
    get_open_vpn_single, create_openvpn_client_cfg_file, create_vpn_connect_file,\
    create_ros_connect_file, create_ssh_connect_file, get_vpc_open_vpn,\
    get_vpc_router_script
from launch_utils.launch import LaunchException, aws_connect, get_amazon_amis,\
    wait_for_multiple_machines_to_run, wait_for_multiple_machines_instances

from launch_utils.testing import get_boto_path, get_test_path, get_test_runner
from vpc_trio import OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP
from launch_utils.monitoring import LATENCY_TIME_BUFFER, record_ping_result,\
    machine_states, update_machine_aws_states, constellation_is_terminated,\
    monitor_launch_state, monitor_simulator, monitor_cloudsim_ping,\
    get_ssh_client
import shutil
from launch_utils.launch_db import get_aws_instance_by_name,\
    get_constellation_to_config_dict



def log(msg, channel = "vrc_constellation"):
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
    ssh_sim = SshClient(sim_machine_dir, sim_key_name, 'ubuntu', sim_ip)
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

def boot_machine(prefix, constellation_name, tcp_port_list, udp_port_list, script, aws_machine_type, aws_ami, credentials_ec2):
    
    constellation = ConstellationState( constellation_name)
    constellation_directory = constellation.get_value("constellation_directory")
    
    
    sg_name = '%s-sg-%s'%(constellation_name, prefix)
    constellation.set_value('%s_security_group_id'% prefix, sg_name)
    # constellation.set_value('%s_security_group' % prefix, sg_name)
    
    ec2conn = aws_connect(credentials_ec2)[0]
    security_group= ec2conn.create_security_group(sg_name, "%s security group for constellation %s" % (prefix, constellation_name))
    
    for port in tcp_port_list:
        security_group.authorize('tcp', port, port, '0.0.0.0/0')
    for port in udp_port_list:
        security_group.authorize('udp', port, port, '0.0.0.0/0')
    security_group.authorize('icmp', -1, -1, '0.0.0.0/0')

    key_name = "key-%s-%s" % (constellation_name, prefix)
    constellation.set_value('%s_key_name'% prefix, key_name)
    
    key_pair = ec2conn.create_key_pair(key_name)
    key_pair.save(constellation_directory)

    res = ec2conn.run_instances( image_id       = aws_ami, 
                             instance_type  = aws_machine_type,
                             #subnet_id      = subnet_id,
                             #private_ip_address=SIM_IP,
                             security_group_ids=[security_group],
                             key_name  = key_name ,
                             user_data = script)
    constellation.set_value('%s_aws_reservation_id'% prefix, res.id)
    

def boot_machines(username, constellation_name, tags, credentials_ec2, constellation_directory):
    
    constellation = ConstellationState( constellation_name)
    
    if constellation.has_value("boot_sequence"):
        if constellation.get_value("boot_sequence") == 'done':
                return
        else:
            shutil.rmtree(constellation_directory)
            os.makedirs(constellation_directory)
            # raise LaunchException("Constellation %s did not boot correctly" % constellation_name)
    constellation.set_value("boot_sequence", "not done")
    
    constellation.set_value("constellation_state", "launching")
    constellation.set_value("error", "")
    
    constellation.set_value("configuration_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")

    init_computer_data(constellation_name, ["sim", "field1","field2", "router" ] )
    constellation = ConstellationState( constellation_name)
    
    constellation.set_value("error", "")
    
    constellation.set_value("setup_sequence", "not done")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("simulation_glx_state", "not running")

    amis = get_amazon_amis(credentials_ec2)
    cluster_ami    = amis['ubuntu_1204_x64_cluster']
    server_ami = amis['ubuntu_1204_x64']
    drc_package_name = "drcsim"

    ROBOT_IP='10.0.0.52'
    TS_IP='10.0.0.50'
    SIM_IP='10.0.0.51'
    OPENVPN_SERVER_IP='11.8.0.1'
    OPENVPN_CLIENT_IP='11.8.0.2'

    router_script = get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP, TS_IP, SIM_IP)
    boot_machine('router', constellation_name, [80,22], [1194], router_script, 't1.micro', server_ami, credentials_ec2)

    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    sim_script = get_drc_startup_script(open_vpn_script, SIM_IP, drc_package_name)
    boot_machine('sim', constellation_name, [80,22], [], sim_script,'cg1.4xlarge',  cluster_ami, credentials_ec2)

    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    field1_script = get_drc_startup_script(open_vpn_script, ROBOT_IP, drc_package_name)
    boot_machine('field1', constellation_name, [80,22], [], field1_script,'cg1.4xlarge',  cluster_ami, credentials_ec2)

    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    field2_script = get_drc_startup_script(open_vpn_script, ROBOT_IP, drc_package_name)
    boot_machine('field2', constellation_name, [80,22], [], field2_script,'cr1.8xlarge',  cluster_ami, credentials_ec2)

    constellation.set_value("boot_sequence", "done")

def configure_machines(constellation_name, tags, credentials_ec2 ):
    ec2conn = aws_connect(credentials_ec2)[0]
    constellation = ConstellationState( constellation_name)
    
    if constellation.get_value("configuration_sequence") == 'done':
        return
    
    constellation_directory = constellation.get_value('constellation_directory')
    
    roles_to_reservations = {}
    roles_to_reservations['router_state'] = constellation.get_value('router_aws_reservation_id')
    roles_to_reservations['sim_state'] = constellation.get_value('sim_aws_reservation_id')
    roles_to_reservations['field1_state'] = constellation.get_value('field1_aws_reservation_id')
    roles_to_reservations['field2_state'] = constellation.get_value('field2_aws_reservation_id')
    
    running_instances = wait_for_multiple_machines_instances(ec2conn, roles_to_reservations, constellation, max_retries = 500, final_state = 'network_setup')
    
    router_aws_id = running_instances['router_state'].id 
    router_ip_address = running_instances['router_state'].ip_address
    constellation.set_value('router_aws_id', router_aws_id)
    constellation.set_value('router_ip_address', router_ip_address)
    
    sim_aws_id = running_instances['sim_state'].id
    sim_ip_address = running_instances['sim_state'].ip_address
    constellation.set_value('sim_aws_id', sim_aws_id)
    constellation.set_value('sim_ip_address', sim_ip_address)
    
    field1_aws_id = running_instances['field1_state'].id
    field1_ip_address = running_instances['field1_state'].ip_address
    constellation.set_value('field1_aws_id', field1_aws_id)
    constellation.set_value('field1_ip_address', field1_ip_address)
    
    field2_aws_id = running_instances['field2_state'].id
    field2_ip_address = running_instances['field2_state'].ip_address
    constellation.set_value('field2_aws_id', field2_aws_id)
    constellation.set_value('field2_ip_address', field2_ip_address)
    
    router_tags = {'Name': '%s_router' % constellation_name}
    router_tags.update(tags)
    
    try:
        ec2conn.create_tags([router_aws_id ], router_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise
    
    sim_tags = {'Name': '%s_sim' % constellation_name}
    sim_tags.update(tags)
    
    try:
        ec2conn.create_tags([ sim_aws_id ], sim_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise   
    
    field1_tags = {'Name': '%s_field1' % constellation_name}
    field1_tags.update(tags)
    
    try:
        ec2conn.create_tags([ field1_aws_id ], field1_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise
    
    field2_tags = {'Name': '%s_field2' % constellation_name}
    field2_tags.update(tags)
    
    try:
        ec2conn.create_tags([ field2_aws_id ], field2_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise
        
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
    
    log('configure_machines done')    

def launch(username, constellation_name, tags, credentials_ec2, constellation_directory ):
    boot_machines(username, constellation_name, tags, credentials_ec2, constellation_directory)
    configure_machines(constellation_name, tags, credentials_ec2)
 

    
def launch_prerelease(username, constellation_name, tags, credentials_ec2, constellation_directory):
    pass


def _launch(username, constellation_name, tags, credentials_ec2, constellation_directory, CONFIGURATION, drc_package_name):

    ec2conn = aws_connect(credentials_ec2)[0]
    constellation = ConstellationState( constellation_name)

    constellation.set_value('constellation_directory', constellation_directory)
    constellation.set_value('tasks', [])

    constellation.set_value('simulation_state', 'nothing')
    constellation.set_value('simulation_aws_state', 'nothing')
    constellation.set_value("gazebo", "not running")
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('simulation_glx_state', "not running")
    constellation.set_value('sim_zip_file', 'not ready')
    constellation.set_value('simulation_latency','[]')


    constellation.set_value('username', username)
    sim_machine_name = "simulator_"+ constellation_name
    constellation.set_value('sim_machine_name', sim_machine_name)
    
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    os.makedirs(sim_machine_dir)

    constellation.set_value('simulation_launch_msg', "setting up security groups")

    sim_sg_name = 'sim-sg-%s'%(constellation_name) 
    sim_security_group= ec2conn.create_security_group(sim_sg_name, "simulator security group for constellation %s" % constellation_name)
    sim_security_group.authorize('tcp', 80, 80, '0.0.0.0/0')     # web
    sim_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')     # ssh
    
    sim_security_group.authorize('tcp', 8080, 8080, '0.0.0.0/0') # ros bridge
    sim_security_group.authorize('tcp', 9090, 9090, '0.0.0.0/0') # ros bridge
    
    sim_security_group.authorize('icmp', -1, -1, '0.0.0.0/0')    # ping        
    sim_security_group.authorize('udp', 1194, 1194, '0.0.0.0/0') # OpenVPN

    sim_security_group_id = sim_security_group.id
    constellation.set_value('sim_security_group_id', sim_security_group_id)

    constellation.set_value('simulation_launch_msg', "creating ssh keys")

    sim_key_name = 'key-sim-%s'%(constellation_name)
    constellation.set_value('sim_key_name', sim_key_name)
    key_pair = ec2conn.create_key_pair(sim_key_name)
    key_pair.save(constellation_directory)

    roles_to_reservations ={}    

    amis = get_amazon_amis(credentials_ec2)
    aws_machine_type = 'cg1.4xlarge'
    aws_disk_image    = amis['ubuntu_1204_x64_cluster']

    open_vpn_script = get_open_vpn_single(OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script, OPENVPN_SERVER_IP, drc_package_name)

    running_machines = {} 
    try:
        constellation.set_value('simulation_state', 'booting')
        constellation.set_value('simulation_launch_msg', "booting")
        
        # start a new machine, using the AWS api via the boto library
        res = ec2conn.run_instances( image_id       = aws_disk_image, 
                                     instance_type  = aws_machine_type,
                                     #subnet_id      = subnet_id,
                                     #private_ip_address=SIM_IP,
                                     security_group_ids=[sim_security_group_id],
                                     key_name=sim_key_name ,
                                     user_data=SIM_SCRIPT)
        
        roles_to_reservations['simulation_state'] = res.id

            # running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries = 150, final_state = 'network_setup')
        count =200
        done = False
        color = "yellow"
        while not done:
            time.sleep(2)
            count -=1
            if count < 0:
                msg = "timeout while waiting for EC2 machine(s) %s" % sim_machine_name
                raise LaunchException(msg)
            
            for r in ec2conn.get_all_instances():
                if r.id ==  res.id:
                    state = r.instances[0].state
                    aws_id = r.instances[0].id 
                    log("%s aws %s state = %s" % (sim_machine_name, aws_id, state))
                    if  state == 'running':
                        running_machines['simulation_state'] = aws_id
                        constellation.set_value('simulation_state', 'network_setup')
                        constellation.set_value('simulation_launch_msg', 'network_setup')
                        
                        done = True
                    constellation.set_value('simulation_aws_state',state)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise                 
            
               
    
    
    simulation_aws_id =  running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)
    
    sim_tags = {'Name':sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([ simulation_aws_id ], sim_tags)
    
    # ec2conn.associate_address(router_aws_id, allocation_id = eip_allocation_id)
    sim_instance = get_ec2_instance(ec2conn, simulation_aws_id)
    sim_ip = sim_instance.ip_address
    
    clean_local_ssh_key_entry(sim_ip)
    
    constellation.set_value('simulation_ip', sim_ip)
    log("%s simulation machine ip %s" % (constellation_name, sim_ip))
    ssh_sim = SshClient(constellation_directory, sim_key_name, 'ubuntu', sim_ip)
    
    networking_done = get_ssh_cmd_generator(ssh_sim,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", 'packages_setup' ,max_retries = 1000)
    #empty_ssh_queue([networking_done], sleep=2)
    
    constellation.set_value('simulation_launch_msg', "waiting for network")
    for g in networking_done:
        time.sleep(1)


    constellation.set_value('simulation_state', 'packages_setup')
    constellation.set_value('simulation_launch_msg', "setting up scripts")
                
    find_file_sim = """
    #!/bin/bash
    
    ls \$1 
    
    """ 
    ssh_sim.create_file(find_file_sim, "cloudsim/find_file_sim.bash")
    
    dpkg_log_sim = """
    #!/bin/bash
    
    tail -1 /var/log/dpkg.log
    
    """ 
    ssh_sim.create_file(dpkg_log_sim, "cloudsim/dpkg_log_sim.bash")
    
    ping_gl = """#!/bin/bash
    
    DISPLAY=localhost:0 timeout 10 glxinfo
    
    """ 
    ssh_sim.create_file(ping_gl, "cloudsim/ping_gl.bash")
    
    ping_gazebo = """#!/bin/bash
    
. /usr/share/drcsim/setup.sh
timeout 5 gztopic list
    
    """ 
    ssh_sim.create_file(ping_gazebo, "cloudsim/ping_gazebo.bash")


    hostname = sim_ip
    file_content = create_openvpn_client_cfg_file(hostname, client_ip = OPENVPN_CLIENT_IP, server_ip = OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(sim_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    
    fname_start_vpn = os.path.join(sim_machine_dir , "start_vpn.bash")    
    file_content = create_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755) # makes the file executable

    fname_ros = os.path.join(sim_machine_dir, "ros.bash")    
    file_content = create_ros_connect_file(OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    key_filename = sim_key_name + '.pem'
    src = os.path.join(constellation_directory, key_filename)
    dst = os.path.join(sim_machine_dir, key_filename)
    copyfile(src ,dst )
    fname_ssh_key =  os.path.join(sim_machine_dir, key_filename)
    os.chmod(fname_ssh_key, 0600)
    
    fname_ssh_sh =  os.path.join(sim_machine_dir,'ssh.bash')
    file_content = create_ssh_connect_file(key_filename, sim_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755) # makes the file executable
            
    fname_zip = os.path.join(sim_machine_dir, "%s.zip" % sim_machine_name)
    
    # wait (if necessary) for openvpn key to have been generated, then
    constellation.set_value('simulation_launch_msg',  "waiting for VPN key generation")
    remote_fname = "/etc/openvpn/static.key"
    sim_key_ready = get_ssh_cmd_generator(ssh_sim, "ls /etc/openvpn/static.key", "/etc/openvpn/static.key", constellation, "simulation_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([sim_key_ready], sleep=2)
    
    vpnkey_fname = os.path.join(sim_machine_dir, "openvpn.key")
    # download it locally for inclusion into the zip file
    
    constellation.set_value('simulation_launch_msg', "downloading sim key to CloudSim server") 
    ssh_sim.download_file(vpnkey_fname, remote_fname) 
    os.chmod(vpnkey_fname,0600)
    
    #creating zip
    files_to_zip = [ fname_ssh_key, 
                     fname_start_vpn,
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    constellation.set_value('simulation_launch_msg', "creating zip file bundle")    
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(sim_machine_name, short_fname)
            fzip.write(fname, zip_name)
    
    constellation.set_value('sim_zip_file', 'ready')
    
    constellation.set_value('simulation_launch_msg', "installing packages")
    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'booting' ,max_retries = 1500)
    empty_ssh_queue([sim_setup_done], sleep=2)
    
    constellation.set_value('simulation_state', "rebooting")
    constellation.set_value('simulation_launch_msg', "rebooting") 
    log("rebooting")
    ssh_sim.cmd("sudo reboot")

    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'running' ,max_retries = 300)
    log("waiting for machine to be booted")
    empty_ssh_queue([sim_setup_done], sleep=2)
    log("machine is ready")

    constellation.set_value('simulation_glx_state', "pending")
    
    gl_retries = 0
    while True:
        log("OpenGL test")
        gl_retries += 1
        time.sleep(10)
        try:
            ping_gl = ssh_sim.cmd("bash cloudsim/ping_gl.bash")
            log("cloudsim/ping_gl.bash = %s" % ping_gl )
            constellation.set_value('simulation_glx_state', "running")
            break
        except Exception, e:
            log("cloudsim/ping_gl.bash = %s" % e )
            if gl_retries > 30:
                log('OpenGL  retry timeout error')
                constellation.set_value('simulation_glx_state', "not running")
                constellation.set_value('error', "%s" % "OpenGL diagnostic failed")
                raise
    
    constellation.set_value('simulation_launch_msg', "reboot Complete")
    constellation.set_value('simulation_state', "running")
    constellation.set_value('constellation_state', 'running')

    log("provisionning done")

    
    
def terminate(constellation_name, credentials_ec2):
#    _terminate(username, 'simulator', constellation_name, credentials_ec2, constellation_directory)
    ec2conn = aws_connect(credentials_ec2)[0]
    constellation = ConstellationState( constellation_name)
    error_msg = ""
    
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
    
    try:
        running_machines =  {}
        for prefix in ['sim', 'router', 'field1', 'field2']:
            machine = '%s_%s' % (constellation_name, prefix)
            instance = get_aws_instance_by_name(machine, credentials_ec2 )
            if instance:
                running_machines[prefix] = instance.id
                
            else:
                error_msg += "Machine <b>%s</b> does not exist<br>" % machine
        
        wait_for_multiple_machines_to_terminate(ec2conn, 
                                                running_machines, 
                                                constellation, 
                                                max_retries = 150 )
        
        constellation.set_value('sim_state', 'terminated')
        constellation.set_value('sim_launch_msg', "terminated")
        constellation.set_value('router_state', 'terminated')
        constellation.set_value('router_launch_msg', "terminated")
        constellation.set_value('field1_state', 'terminated')
        constellation.set_value('field1_launch_msg', "terminated")
        constellation.set_value('field2_state', 'terminated')
        constellation.set_value('field2_launch_msg', "terminated")

    except Exception, e:
        error_msg += "<b>Machine shutdown</b>: %s<br>" % e
        constellation.set_value('error', error_msg)        
        log ("error killing instances: %s" % e)
    
    for prefix in ['sim','router', 'field1', 'field2']:
        key_name = "key-%s-%s" % (constellation_name, prefix)
        try:
            ec2conn.delete_key_pair(key_name)
        except Exception, e:
            error_msg += "<b>key</b>: %s<br>" % e
            constellation.set_value('error', error_msg)        
            log("error cleaning up simulation key %s: %s" % (key_name, e))
        
        security_group_name =  '%s-sg-%s' % (constellation_name, prefix) 
        try:    
             
            ec2conn.delete_security_group(name = security_group_name)
        except Exception, e:
            error_msg += "<b>security group</b>: %s<br>" % e
            constellation.set_value('error', error_msg)        
            log("error cleaning up security group %s: %s" % (security_group_name, e))

    constellation.set_value('constellation_state', 'terminated')

    



    

class MonitorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxb49a97c4'
        cred = get_boto_path()
        
        monitor(user, const, cred, 1)
        
  
class VrcCase(unittest.TestCase):
    
    def test_delete_vrc_constellations(self):
        credentials_ec2  = get_boto_path()
        constellations = []
        d = get_constellation_to_config_dict(credentials_ec2)
        for const, conf in d.iteritems():
            if conf == "vrc_constellation":
                constellations.append(const)
        
        for constellation_name in constellations:
            terminate(constellation_name, credentials_ec2)
    
    def atest_const_2_config(self):
        credentials_ec2  = get_boto_path()
        d = get_constellation_to_config_dict(credentials_ec2)
        for const, conf in d.iteritems():
            print("const: %s = %s"%(const,conf))
    
    def atest_monitor(self):
        
        self.constellation_name =  "cxf44f7040"
        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
        
    def stest_launch(self):
        
        
        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        
        CONFIGURATION = 'vrc_constellation'
        
        
#        
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
        constellation.set_value("configuration", 'vrc_constellation')
        
        self.tags = {'TestCase':CONFIGURATION, 'configuration': CONFIGURATION, 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"}
        launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.constellation_directory)
                
        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
        
        terminate(self.constellation_name, self.credentials_ec2)
        
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        #terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)    