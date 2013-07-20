from __future__ import print_function

import unittest
import os
import time


import logging
import redis

import boto
from boto.pyami.config import Config as BotoConfig

from launch_utils import get_unique_short_name
from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance 

from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient
from launch_utils import get_ssh_cmd_generator, empty_ssh_queue
from launch_utils import ConstellationState
from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_drc_startup_script,\
    get_vpc_router_script, get_vpc_open_vpn, create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file, create_ssh_connect_file

from launch_utils.testing import get_boto_path, get_test_path, get_test_runner
import zipfile
from shutil import copyfile

from launch_utils.monitoring import  update_machine_aws_states,\
    constellation_is_terminated, get_ssh_client, monitor_launch_state,\
    monitor_simulator, monitor_ssh_ping, monitor_cloudsim_ping
from launch_utils.launch import aws_connect, get_amazon_amis
from launch_utils.traffic_shaping import run_tc_command
from launch_utils.launch_db import log_msg


ROBOT_IP='10.0.0.52'
TS_IP='10.0.0.50'
SIM_IP='10.0.0.51'
OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)



def update(constellation_name):
    """
    Upadate the constellation software on the servers.
    This function is a plugin function that should be implemented by 
    each constellation type
    """
    constellation = ConstellationState( constellation_name)
    constellation_directory = constellation.get_value('constellation_directory')
    
    # Do the software update here, via ssh
    

def create_vcp_router_securtity_group(ec2conn, sg_name, constellation_name, vpc_id, vpn_subnet):
    sg = ec2conn.create_security_group(sg_name, 'Security group for constellation %s' % (constellation_name), vpc_id)
    sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
    sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
    sg.authorize('udp' , 0, 65535, vpn_subnet)
    sg.authorize('tcp' , 0, 65535, vpn_subnet)
    return sg.id


def create_vcp_internal_securtity_group(ec2conn, sg_name, constellation_name, vpc_id, vpn_subnet):
    sg = ec2conn.create_security_group(sg_name, 'Security group for constellation %s' % (constellation_name), vpc_id)
    sg.authorize('icmp', -1, -1, vpn_subnet)
    sg.authorize('tcp',  0, 65535, vpn_subnet)
    sg.authorize('udp' , 0, 65535, vpn_subnet)
    # Also allow all traffic from the OpenVPN client
    openvpn_client_addr = '%s/32'%(OPENVPN_CLIENT_IP)
    sg.authorize('icmp', -1, -1, openvpn_client_addr)
    sg.authorize('tcp', 0, 65535, openvpn_client_addr)
    sg.authorize('udp' , 0, 65535, openvpn_client_addr)
    return sg.id


def start_task(constellation, task):
    log("** SIMULATOR *** start_task %s" % task['task_id'])

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation, 'router_machine_name', 'router_key_pair_name', 'router_public_ip', latency, up, down)

    log("** START SIMULATOR ***")
    start_simulator(constellation, task['ros_package'], task['ros_launch'], task['ros_args'], task['timeout'])


def stop_task(constellation):
    log("** SIMULATOR *** STOP TASK %s ***" % constellation)
    log("** stop simulator ***")
    stop_simulator(constellation)
    latency = 0 
    up = -1
    down = -1
    log("** TC COMMAND ***")
    run_tc_command(constellation, 'router_machine_name', 'router_key_pair_name', 'router_public_ip', latency, up, down)


def launch_prerelease(username, constellation_name, tags, credentials_ec2, constellation_directory ):


    # call _launch with small instance machine types with simple scripts and call  
    CONFIGURATION = "vpc_trio_prerelease"

    ROBOT_AWS_TYPE = 'cg1.4xlarge'

    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    ROBOT_SCRIPT = get_drc_startup_script(open_vpn_script, ROBOT_IP, drc_package_name = "drcsim-prerelease")


    SIM_AWS_TYPE = 'cg1.4xlarge'
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script, SIM_IP, drc_package_name = "drcsim-prerelease")
    ROUTER_AWS_TYPE='t1.micro'
    ROUTER_SCRIPT = get_vpc_router_script(OPENVPN_SERVER_IP,
                                          OPENVPN_CLIENT_IP,
                                          TS_IP,
                                          SIM_IP)

    _launch(username, constellation_name, tags, credentials_ec2, constellation_directory,
                        ROUTER_AWS_TYPE,
                        ROUTER_SCRIPT,
                        ROBOT_AWS_TYPE,
                        ROBOT_SCRIPT,
                        SIM_AWS_TYPE,
                        SIM_SCRIPT, 
                        CONFIGURATION)


def launch(username, constellation_name, tags, credentials_ec2, constellation_directory ):
    # call _launch with small instance machine types with simple scripts and call  
    CONFIGURATION = "vpc_trio"

    ROBOT_AWS_TYPE = 'cg1.4xlarge'
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    ROBOT_SCRIPT = get_drc_startup_script(open_vpn_script, ROBOT_IP, "drcsim")

    SIM_AWS_TYPE = 'cg1.4xlarge'
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script, SIM_IP, "drcsim")
    ROUTER_AWS_TYPE = 't1.micro'
    ROUTER_SCRIPT = get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP,
                                          TS_IP, SIM_IP)

    _launch(username,
            constellation_name, tags,
            credentials_ec2,
            constellation_directory,
            ROUTER_AWS_TYPE,
            ROUTER_SCRIPT,
            ROBOT_AWS_TYPE,
            ROBOT_SCRIPT,
            SIM_AWS_TYPE,
            SIM_SCRIPT,
            CONFIGURATION)


def terminate_prerelease(username, constellation_name, constellation_directory):
    _terminate(username, constellation_name,  constellation_directory, "vpc_trio_prerelease")


def terminate(constellation_name):
    # call terminate with the appropriate configuration name
    username =""
    constellation_dict = get_constellation_data(  constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    _terminate(username, constellation_name, constellation_directory, "vpc_trio")


def monitor_prerelease(username, constellation_name,  counter):
    m = _monitor(username, constellation_name,  counter, "vpc_trio_prerelease")
    return m


def monitor(constellation_name,  counter):
    m =_monitor( constellation_name,  counter, "vpc_trio")
    return m


def start_simulator(constellation_name,
                    package_name,
                    launch_file_name,
                    launch_args, timeout):

    log("vpc_trio start_simulator")
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_key_pair_name = constellation_dict['router_key_pair_name']
    router_ip = constellation_dict['router_public_ip']

    try:
        c = "bash cloudsim/start_sim.bash " + package_name + " " + launch_file_name + " " + launch_args
        cmd = c.strip()
        ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
        r = ssh_router.cmd(cmd)
        log('start_simulator %s' % r)
    except Exception, e:
        log('start_simulator error %s' % e)


def stop_simulator( constellation_name):
    log("vpc_trio stop_simulator")
    constellation_dict = get_constellation_data( constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_key_pair_name    = constellation_dict['router_key_pair_name']
    router_ip    = constellation_dict['router_public_ip']
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
    try:
        r = ssh_router.cmd(cmd)
        log('stop_simulator %s' % r)
    except Exception, e:
        log('error stop_simulator %s' % e)


def _monitor(constellation_name,  counter, CONFIGURATION):

    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True

    constellation = ConstellationState(constellation_name)

    router_state = constellation.get_value('router_state')
    robot_state = constellation.get_value('robot_state')
    simulation_state = constellation.get_value('simulation_state')

    update_machine_aws_states( constellation_name, {'router_aws_id':'router_aws_state' ,'robot_aws_id': "robot_aws_state", 'simulation_aws_id':"simulation_aws_state"}) 

    ssh_router = get_ssh_client(constellation_name, router_state,'router_public_ip', 'router_key_pair_name' )

    monitor_launch_state(constellation_name, ssh_router, router_state, "bash cloudsim/dpkg_log_router.bash", 'router_launch_msg' )
    monitor_launch_state(constellation_name, ssh_router, robot_state,  "bash cloudsim/dpkg_log_robot.bash", 'robot_launch_msg' )
    monitor_launch_state(constellation_name, ssh_router, simulation_state,  "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg' )        

    monitor_ssh_ping(constellation_name, ssh_router, SIM_IP, 'simulation_latency')
    monitor_ssh_ping(constellation_name, ssh_router, ROBOT_IP, 'robot_latency')


    monitor_cloudsim_ping(constellation_name, 'router_public_ip', 'simulation_latency')

    monitor_simulator(constellation_name, ssh_router)

    return False  # not done yet




def create_zip_file(zip_file_path, short_name, files_to_zip):
    with zipfile.ZipFile(zip_file_path, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(short_name, short_fname)
            fzip.write(fname, zip_name)


def _launch(username,
            constellation_name,
            tags,
            constellation_directory,
            ROUTER_AWS_TYPE,
            ROUTER_SCRIPT,
            ROBOT_AWS_TYPE,
            ROBOT_SCRIPT,

            SIM_AWS_TYPE,
            SIM_SCRIPT,
            CONFIGURATION):

    log("new trio constellation: %s" % constellation_name) 

    amis = get_amazon_amis()
    print (amis)

    SIM_AWS_IMAGE = amis['ubuntu_1204_x64_cluster']
    if SIM_AWS_TYPE == 't1.micro':
        SIM_AWS_IMAGE = amis['ubuntu_1204_x64']

    ROBOT_AWS_IMAGE = amis['ubuntu_1204_x64_cluster']
    if ROBOT_AWS_TYPE == 't1.micro':
        ROBOT_AWS_IMAGE = amis['ubuntu_1204_x64']

    ROUTER_AWS_IMAGE = amis['ubuntu_1204_x64']

    ec2conn, vpcconn = aws_connect()
    constellation = ConstellationState(constellation_name)

    constellation.set_value('sim_ip', SIM_IP)
    constellation.set_value('router_ip', TS_IP)
    constellation.set_value('robot_ip', ROBOT_IP)

    constellation.set_value('router_state', 'nothing')
    constellation.set_value('robot_state', 'nothing')
    constellation.set_value('simulation_state', 'nothing')

    constellation.set_value('router_aws_state', 'nothing')
    constellation.set_value('robot_aws_state', 'nothing')
    constellation.set_value('simulation_aws_state', 'nothing')
    constellation.set_value('constellation_directory', constellation_directory)

    constellation.set_value("gazebo", "not running")

    constellation.set_value('router_launch_msg', "starting")
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('robot_launch_msg', "starting")

    constellation.set_value('simulation_glx_state', "not running")

    constellation.set_value('robot_zip_file', 'not ready')
    constellation.set_value('router_zip_file', 'not ready')
    constellation.set_value('sim_zip_file', 'not ready')

    constellation.set_value('router_latency', '[]')
    constellation.set_value('robot_latency', '[]')
    constellation.set_value('simulation_latency', '[]')

    sim_machine_name = "simulator_" + constellation_name
    constellation.set_value('sim_machine_name', sim_machine_name)

    robot_machine_name = "field_computer_" + constellation_name
    constellation.set_value('robot_machine_name', robot_machine_name)

    router_machine_name = "router_" + constellation_name
    constellation.set_value('router_machine_name', router_machine_name)

    #  monitor(username, constellation_name, credentials_ec2, constellation_directory )
    constellation.set_value('router_launch_msg', "acquiring public ip")
    try:
        router_elastic_ip = ec2conn.allocate_address('vpc')
        router_eip_allocation_id = router_elastic_ip.allocation_id
        constellation.set_value('router_eip_allocation_id', router_eip_allocation_id)
        router_ip = router_elastic_ip.public_ip
        constellation.set_value('router_public_ip', router_ip)
        log("router elastic ip %s" % router_elastic_ip.public_ip)
        clean_local_ssh_key_entry(router_ip)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    try:
        robot_elastic_ip = ec2conn.allocate_address('vpc')
        robot_eip_allocation_id = robot_elastic_ip.allocation_id
        constellation.set_value('robot_eip_allocation_id', robot_eip_allocation_id)
        robot_public_ip = robot_elastic_ip.public_ip
        constellation.set_value('robot_public_ip', robot_public_ip)
        log("robot elastic ip %s" % robot_elastic_ip.public_ip)
        #clean_local_ssh_key_entry(robot_public_ip)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    try:
        sim_elastic_ip = ec2conn.allocate_address('vpc')
        sim_eip_allocation_id = sim_elastic_ip.allocation_id
        constellation.set_value('sim_eip_allocation_id', sim_eip_allocation_id)
        sim_public_ip = sim_elastic_ip.public_ip
        constellation.set_value('sim_public_ip', sim_public_ip)
        log("sim elastic ip %s" % sim_elastic_ip.public_ip)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    #
    #  VPC configuration
    #
    vpc_id = None
    subnet_id = None
    try:
        VPN_PRIVATE_SUBNET = '10.0.0.0/24'
        constellation.set_value('router_launch_msg',
                                "creating virtual private network")
        vpc_id = vpcconn.create_vpc(VPN_PRIVATE_SUBNET).id
        constellation.set_value('vpc_id', vpc_id)
        log("VPC %s" % vpc_id)
        availability_zone = boto.config.get('Boto', 'ec2_region_name')
        subnet_id = vpcconn.create_subnet(vpc_id,
                                  VPN_PRIVATE_SUBNET,
                                  availability_zone=availability_zone).id
        constellation.set_value('subnet_id', subnet_id)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    #
    # Security groups
    #
    constellation.set_value('router_launch_msg',  "setting up security groups")
    sim_security_group_id = None
    robot_security_group_id = None
    router_security_group_id = None

    try:
        router_sg_name = 'router-sg-%s' % (constellation_name)
        router_security_group_id = create_vcp_router_securtity_group(ec2conn,
                router_sg_name, constellation_name, vpc_id, VPN_PRIVATE_SUBNET)
        constellation.set_value('router_security_group_id',
                                router_security_group_id)
    except Exception, e:
        constellation.set_value('error',  "security group error: %s" % e)
        raise
    try:
        robot_sg_name = 'robot-sg-%s' % (constellation_name)
        robot_security_group_id = create_vcp_internal_securtity_group(ec2conn,
                robot_sg_name, constellation_name, vpc_id, VPN_PRIVATE_SUBNET)
        constellation.set_value('robot_security_group_id',
                                robot_security_group_id)
    except Exception, e:
        constellation.set_value('error', "security group error: %s" % e)
        raise

    try:
        sim_sg_name = 'sim-sg-%s' % (constellation_name)
        sim_security_group_id = create_vcp_internal_securtity_group(ec2conn,
                sim_sg_name, constellation_name, vpc_id, VPN_PRIVATE_SUBNET)
        constellation.set_value('sim_security_group_id', sim_security_group_id)
    except Exception, e:
        constellation.set_value('error', "security group error: %s" % e)
        raise
    #
    # Internet Gateway
    #
    constellation.set_value('router_launch_msg', "setting up internet gateway")
    igw_id = vpcconn.create_internet_gateway().id
    constellation.set_value('igw_id', igw_id)
    vpcconn.attach_internet_gateway(igw_id, vpc_id)

    constellation.set_value('router_launch_msg',  "creating routing tables")
    route_table_id = vpcconn.create_route_table(vpc_id).id
    constellation.set_value('route_table_id', route_table_id)

    vpcconn.create_route(route_table_id, '0.0.0.0/0', igw_id)
    route_table_association_id = vpcconn.associate_route_table(route_table_id,
                                                               subnet_id)
    constellation.set_value('route_table_association_id',
                            route_table_association_id)

    #
    # KEY pairs for SSH access
    #
    constellation.set_value('router_launch_msg',  "creating routing tables")
    router_key_pair_name = 'key-router-%s' % (constellation_name)
    constellation.set_value('router_launch_msg', "creating ssh keys")
    try:
        key_pair = ec2conn.create_key_pair(router_key_pair_name)
        key_pair.save(constellation_directory)
    except Exception, e:
        constellation.set_value("key error: %s" % e)
        raise

    constellation.set_value('router_key_pair_name', router_key_pair_name)

    robot_key_pair_name = 'key-robot-%s'%(constellation_name)

    try:
        key_pair = ec2conn.create_key_pair(robot_key_pair_name)
        key_pair.save(constellation_directory)
    except Exception, e:
        constellation.set_value('error', "key error: %s" % e)
        raise

    constellation.set_value('robot_key_pair_name', robot_key_pair_name)

    sim_key_pair_name = 'key-sim-%s'%(constellation_name)
    try:
        key_pair = ec2conn.create_key_pair(sim_key_pair_name)
        key_pair.save(constellation_directory)
    except Exception, e:
        constellation.set_value('error', "key error: %s" % e)
        raise

    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    roles_to_reservations ={}

    try:
        constellation.set_value('robot_launch_msg',  "booting")
        res = ec2conn.run_instances(ROBOT_AWS_IMAGE,
                                 instance_type=ROBOT_AWS_TYPE,
                                 subnet_id=subnet_id,
                                 private_ip_address=ROBOT_IP,
                                 security_group_ids=[robot_security_group_id],
                                 key_name=robot_key_pair_name,
                                 user_data=ROBOT_SCRIPT)
        roles_to_reservations['robot_state'] = res.id
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    try:
        constellation.set_value('simulation_launch_msg', "booting")
        res = ec2conn.run_instances(SIM_AWS_IMAGE,
                                 instance_type=SIM_AWS_TYPE,
                                 subnet_id=subnet_id,
                                 private_ip_address=SIM_IP,
                                 security_group_ids=[sim_security_group_id],
                                 key_name=sim_key_pair_name,
                                 user_data=SIM_SCRIPT)
        roles_to_reservations['simulation_state'] = res.id
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    try:
        constellation.set_value('router_launch_msg',   "booting")
        res = ec2conn.run_instances(ROUTER_AWS_IMAGE, instance_type=ROUTER_AWS_TYPE,
                                             subnet_id=subnet_id,
                                             private_ip_address=TS_IP,
                                             security_group_ids=[router_security_group_id ],
                                             key_name= router_key_pair_name,
                                             user_data=ROUTER_SCRIPT)
        roles_to_reservations['router_state'] = res.id
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    running_machines = wait_for_multiple_machines_to_run(ec2conn,
        roles_to_reservations,
        constellation, max_retries=500, final_state='network_setup')

    # monitor_constellation(username, constellation_name, credentials_ec2, constellation_directory )

    router_aws_id =  running_machines['router_state']
    constellation.set_value('router_aws_id', router_aws_id)

    robot_aws_id =  running_machines['robot_state']
    constellation.set_value('robot_aws_id', robot_aws_id)

    simulation_aws_id =  running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)

    constellation.set_value('router_launch_msg',   "setting machine tags")
    router_tags = {'Name':router_machine_name}
    router_tags.update(tags)

    try:
        ec2conn.create_tags([router_aws_id ], router_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    sim_tags = {'Name':sim_machine_name}
    sim_tags.update(tags)

    try:
        ec2conn.create_tags([ simulation_aws_id ], sim_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    robot_tags = {'Name':robot_machine_name}
    robot_tags.update(tags)

    try:
        ec2conn.create_tags([ robot_aws_id ], robot_tags)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    constellation.set_value('router_launch_msg',   "assigning elastic IPs")

    try:
        ec2conn.associate_address(router_aws_id, allocation_id = router_eip_allocation_id)
        ec2conn.associate_address(robot_aws_id, allocation_id = robot_eip_allocation_id)
        ec2conn.associate_address(simulation_aws_id, allocation_id = sim_eip_allocation_id)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise

    router_instance = get_ec2_instance(ec2conn, router_aws_id)
    router_instance.modify_attribute('sourceDestCheck', False)

    constellation.set_value('router_launch_msg', "setting up packages")
    ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
    router_setup_done = get_ssh_cmd_generator(ssh_router,"ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "router_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([router_setup_done], sleep=2)

    #
    # Send the simulator and field computer keys to the router
    #
    constellation.set_value('router_launch_msg', "acquiring keys")
    local = os.path.join(constellation_directory, "%s.pem" %  sim_key_pair_name )
    remote = os.path.join("cloudsim", "%s.pem" %  sim_key_pair_name ) 
    ssh_router.upload_file(local, remote)

    local = os.path.join(constellation_directory, "%s.pem" % robot_key_pair_name)
    remote = os.path.join("cloudsim", "%s.pem" % robot_key_pair_name)
    ssh_router.upload_file(local, remote)

    constellation.set_value('router_launch_msg', "generating scripts")
    dpkg_log_robot = """
    #!/bin/bash

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "tail -1 /var/log/dpkg.log"

    """ % ( robot_key_pair_name, ROBOT_IP)
    ssh_router.create_file(dpkg_log_robot, "cloudsim/dpkg_log_robot.bash")

    dpkg_log_router = """
    #!/bin/bash

tail -1 /var/log/dpkg.log

    """
    ssh_router.create_file(dpkg_log_router, "cloudsim/dpkg_log_router.bash")

    find_file_robot = """
    #!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "ls \$1" 
    
    """ % ( robot_key_pair_name , ROBOT_IP)
    ssh_router.create_file(find_file_robot, "cloudsim/find_file_robot.bash")

    #DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" && pwd )"
    #ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i \$DIR/%s.pem ubuntu@%s "ls \$1"
        
    find_file_sim = """
    #!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "ls \$1" 
    
    """ % ( sim_key_pair_name, SIM_IP)
    ssh_router.create_file(find_file_sim, "cloudsim/find_file_sim.bash")
    
    dpkg_log_sim = """
    #!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "tail -1 /var/log/dpkg.log"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(dpkg_log_sim, "cloudsim/dpkg_log_sim.bash")
    
    ping_gl = """#!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "DISPLAY=localhost:0 timeout 10 glxinfo"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(ping_gl, "cloudsim/ping_gl.bash")
    
    ping_gazebo = """#!/bin/bash
    
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s ". /usr/share/drcsim/setup.sh; timeout 5 gztopic list"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(ping_gazebo, "cloudsim/ping_gazebo.bash")
    
    stop_sim = """#!/bin/bash

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "killall -INT roslaunch"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(stop_sim, "cloudsim/stop_sim.bash")
    
    start_sim = """#!/bin/bash
     
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "bash cloudsim/start_sim.bash \$1 \$2 \$3"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(start_sim, "cloudsim/start_sim.bash")

    sim_reboot = """#!/bin/bash
    
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "sudo reboot"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(sim_reboot, "cloudsim/sim_reboot.bash")
    
    robot_reboot = """#!/bin/bash
    
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "sudo reboot"
    
    """ % (robot_key_pair_name , ROBOT_IP)
    ssh_router.create_file(robot_reboot, "cloudsim/robot_reboot.bash")    
    constellation.set_value('router_launch_msg',   "creating key zip file bundle")
    
    
    #
    # ZIP files
    # First, create 3 directories (using machine names) and copy pem key files there 

    router_machine_dir = os.path.join(constellation_directory, router_machine_name)
    os.makedirs(router_machine_dir )
    router_key_short_filename = router_key_pair_name + '.pem'
    router_key_path =  os.path.join(router_machine_dir, router_key_short_filename)
    copyfile(os.path.join(constellation_directory, router_key_short_filename), router_key_path)
    os.chmod(router_key_path, 0600)
    
    robot_machine_dir = os.path.join(constellation_directory, robot_machine_name)
    os.makedirs(robot_machine_dir )
    robot_key_short_filename = robot_key_pair_name + '.pem'
    robot_key_path =  os.path.join(robot_machine_dir, robot_key_short_filename)
    copyfile(os.path.join(constellation_directory,   robot_key_short_filename), robot_key_path)
    os.chmod(robot_key_path, 0600)
    
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    os.makedirs(sim_machine_dir )
    sim_key_short_filename = sim_key_pair_name + '.pem'
    sim_key_path =  os.path.join(sim_machine_dir, sim_key_short_filename)
    copyfile(os.path.join(constellation_directory,   sim_key_short_filename), sim_key_path)    
    os.chmod(sim_key_path, 0600)

    # create router zip file with keys
    # This file is kept on the server and provides the user with:
    #  - key file for ssh access to the router
    #  - openvpn key
    #  - scripts to connect with ssh, openvpn, ROS setup 
    #  
    #
    hostname = router_ip
    file_content = create_openvpn_client_cfg_file(hostname, client_ip = OPENVPN_CLIENT_IP, server_ip = OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(router_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    
    fname_start_vpn = os.path.join(router_machine_dir , "start_vpn.bash")    
    file_content = create_vpc_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755)
    
    fname_ros = os.path.join(router_machine_dir, "ros.bash")    
    file_content = create_ros_connect_file(machine_ip=OPENVPN_CLIENT_IP, master_ip=SIM_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)

    
    fname_ssh_sh =  os.path.join(router_machine_dir,'router_ssh.bash')
    file_content = create_ssh_connect_file(router_key_short_filename, router_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    # wait (if necessary) for openvpn key to have been generated
    constellation.set_value('router_launch_msg',   "waiting for key generation") 
    remote_fname = "/etc/openvpn/static.key"
    router_key_ready = get_ssh_cmd_generator(ssh_router, "ls /etc/openvpn/static.key", "/etc/openvpn/static.key", constellation, "simulation_state", 'running' ,max_retries = 100)
    empty_ssh_queue([router_key_ready], sleep=2)
    
    vpnkey_fname = os.path.join(router_machine_dir, "openvpn.key")
    
    # download it locally for inclusion into the zip file
    constellation.set_value('router_launch_msg',   "downloading router vpn key to CloudSim server") 
    ssh_router.download_file(vpnkey_fname, remote_fname) 
    os.chmod(vpnkey_fname, 0600)
    
    #creating zip
    files_to_zip = [ router_key_path, 
                     fname_start_vpn,
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    router_fname_zip = os.path.join(router_machine_dir, "%s.zip" % router_machine_name)
    create_zip_file(router_fname_zip, router_machine_name, files_to_zip)
    constellation.set_value('router_zip_file', 'ready')
    
    # create simulator zip file with keys
    # This file is kept on the server and provides the user with:
    #  - key file for ssh access to the router
    #  - openvpn key
    #  - scripts to connect with ssh, openvpn, ROS setup 
    
    
    constellation.set_value('simulation_launch_msg', "creating zip file bundle")
    fname_ssh_sh =  os.path.join(sim_machine_dir,'simulator_ssh.bash')
    file_content = create_ssh_connect_file(sim_key_short_filename, SIM_IP)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)    
            
    files_to_zip = [ sim_key_path, 
                     fname_ssh_sh,]
    
    sim_fname_zip = os.path.join(sim_machine_dir, "%s.zip" % sim_machine_name)
    create_zip_file(sim_fname_zip, sim_machine_name, files_to_zip)
    constellation.set_value('sim_zip_file', 'ready')

    # create field computer zip file with keys
    # This file is kept on the server and provides the user with:
    #  - key file for ssh access to the router
    #  - openvpn key
    #  - scripts to connect with ssh, openvpn, ROS setup 
    constellation.set_value('robot_launch_msg',   "creating zip file bundle")
    fname_ssh_sh =  os.path.join(robot_machine_dir,'robot_ssh.bash')
    file_content = create_ssh_connect_file(robot_key_short_filename, ROBOT_IP)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)
                
    files_to_zip = [ robot_key_path, 
                     fname_ssh_sh,]

    robot_fname_zip = os.path.join(robot_machine_dir, "%s.zip" % robot_machine_name)
    create_zip_file(robot_fname_zip, robot_machine_name, files_to_zip)
    constellation.set_value('robot_zip_file', 'ready')
    
    constellation.set_value('router_state', 'running')
    constellation.set_value('router_launch_msg',   "running")

    robot_ssh_ready = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "robot_state", "packages_setup", max_retries = 500)
    sim_ssh_ready = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", "packages_setup", max_retries = 500)
    
    
    robot_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "robot_state", "running",  max_retries = 250)
    sim_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", "running",max_retries = 250)
    
    empty_ssh_queue([robot_ssh_ready, sim_ssh_ready, robot_done, sim_done], 2)

    #
    # REBOOT the 2 large machines
    #
    constellation.set_value('simulation_state', "rebooting")
    constellation.set_value('simulation_launch_msg', "rebooting")
    ssh_router.cmd("bash cloudsim/sim_reboot.bash")
    
    constellation.set_value('robot_state', "rebooting")
    constellation.set_value('robot_launch_msg', "rebooting")
    ssh_router.cmd("bash cloudsim/robot_reboot.bash")
    
    log("Waiting for reboot to be done")
    time.sleep(15)
    
    robot_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "robot_state", "running",  max_retries = 500)
    sim_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", "running",max_retries = 500)
    empty_ssh_queue([robot_done, sim_done], 2)
    
    
    constellation.set_value('simulation_glx_state', "pending")
    
    if CONFIGURATION == "vpc_micro_trio":
        constellation.set_value('simulation_glx_state', "not running")
    else:
        gl_retries = 0
        while True:
            gl_retries += 1
            time.sleep(10)
            try:
                ping_gl = ssh_router.cmd("bash cloudsim/ping_gl.bash")
                log("bash cloudsim/ping_gl.bash = %s" % ping_gl )
                constellation.set_value('simulation_glx_state', "running")
                break
            except Exception, e:
                if gl_retries > 30:
                    constellation.set_value('simulation_glx_state', "not running")
                    constellation.set_value('error', "%s" % "OpenGL diagnostic failed")
                    raise
            
    constellation.set_value('constellation_state', 'running')
    constellation.set_value('simulation_launch_msg', "running")
    constellation.set_value('robot_launch_msg', "running")
    log("provisioning done")
    
    
def _terminate( constellation_name, constellation_directory, CONFIGURATION):

    resources = get_constellation_data( constellation_name)
    constellation = ConstellationState( constellation_name)
    
    constellation.set_value('router_launch_msg', "terminating")
    constellation.set_value('simulation_launch_msg', "terminating")
    constellation.set_value('robot_launch_msg', "terminating")
    constellation.set_value('router_state', "terminating")
    constellation.set_value('simulation_state', "terminating")
    constellation.set_value('robot_state', "terminating")
    constellation.set_value('simulation_glx_state', "not running")
    ec2conn, vpcconn = aws_connect()

    log("terminate_vpc_trio [constellation_name=%s" % ( constellation_name) )

    #log("resources: %s" %   pprint.pformat(resources) )
    error_msg = ""
    try:
        route_table_association_id =  resources['route_table_association_id']
        route_table_id =  resources['route_table_id']
        vpcconn.disassociate_route_table(route_table_association_id)
        vpcconn.delete_route(route_table_id, '0.0.0.0/0')
        vpcconn.delete_route_table(route_table_id)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        log("error cleaning up routing table: %s" % e)
    
    try:
        running_machines =  {}
        running_machines['router_aws_state'] = resources['router_aws_id']
        running_machines['robot_aws_state'] = resources['robot_aws_id']
        running_machines['simulation_aws_state'] = resources['simulation_aws_id']

        wait_for_multiple_machines_to_terminate(ec2conn, 
                                                running_machines, 
                                                constellation, 
                                                max_retries = 150)
        
        constellation.set_value('router_state', "terminated")
        constellation.set_value('robot_state', "terminated")
        constellation.set_value('simulation_state', "terminated")
        constellation.set_value('router_launch_msg', "terminated")
        constellation.set_value('simulation_launch_msg', "terminated")
        constellation.set_value('robot_launch_msg', "terminated")
    
        print ('Waiting after killing instances...')
        time.sleep(20.0)
    except Exception, e:
        error_msg += "<b>Machine shutdown</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log ("error killing instances: %s" % e)
        
    router_key_pair_name = None
    try:
        router_key_pair_name =  resources[ 'router_key_pair_name']
        ec2conn.delete_key_pair(router_key_pair_name)
    except Exception, e:
        error_msg += "<b>Router key</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up router key %s: %s" % (router_key_pair_name, e))
        
    robot_key_pair_name = None 
    try:
        robot_key_pair_name = resources[ 'robot_key_pair_name']
        ec2conn.delete_key_pair(robot_key_pair_name)
    except Exception, e:
        error_msg += "<b>Field computer key</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up robot key %s: %s" % (robot_key_pair_name, e))
        
    sim_key_pair_name = None
    try:
        sim_key_pair_name =  resources[ 'sim_key_pair_name']
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception, e:
        error_msg += "<b>Simulator key</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))

    router_security_group_id = None
    try:
        router_security_group_id =  resources['router_security_group_id' ]
        ec2conn.delete_security_group(group_id = router_security_group_id)
    except Exception, e:
        error_msg += "<b>Router security group</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up router security group %s: %s" % (router_security_group_id, e))

    robot_security_group_id = None
    try:
        robot_security_group_id =  resources['robot_security_group_id' ]
        ec2conn.delete_security_group(group_id = robot_security_group_id)
    except Exception, e:
        error_msg += "<b>Field computer security group</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up robot security group %s: %s" % (robot_security_group_id, e))

    sim_security_group_id = None
    try:
        sim_security_group_id = resources['sim_security_group_id' ]
        ec2conn.delete_security_group(group_id = sim_security_group_id)
    except Exception, e:
        error_msg += "<b>Simulator security group</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up sim security group %s: %s" % (sim_security_group_id, e))
    router_eip_allocation_id = None
    try:
        router_eip_allocation_id =  resources['router_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = router_eip_allocation_id)
    except Exception, e:
        error_msg += "<b>Router IP address</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        print("error cleaning up router elastic ip: %s" % e)
    try:
        eip_allocation_id = resources['robot_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = eip_allocation_id)
    except Exception, e:
        error_msg += "<b>Field computer IP address</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        print("error cleaning up robot elastic ip: %s" % e)
    try:
        eip_allocation_id = resources['sim_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = eip_allocation_id)
    except Exception, e:
        error_msg += "<b>Simulator IP address</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        print("error cleaning up sim elastic ip: %s" % e)
    try:
        igw_id  = resources['igw_id']
        vpc_id = resources['vpc_id']
        vpcconn.detach_internet_gateway(igw_id, vpc_id)
        vpcconn.delete_internet_gateway(igw_id)
    except Exception, e:
        error_msg += "<b>Internet gateway</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up internet gateway: %s" % e)

    try:
        subnet_id  = resources['subnet_id']
        vpcconn.delete_subnet(subnet_id)
    except Exception, e:
        error_msg += "<b>Subnet</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up subnet: %s" % e) 

    try:
        vpc_id =  resources['vpc_id']
        vpcconn.delete_vpc(vpc_id)
    except Exception, e:
        error_msg += "<b>VPC</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up vpc: %s" % e )

    constellation.set_value('constellation_state', 'terminated')


class DbCase(unittest.TestCase):
    
    def test_set_get(self):
        
        user_or_domain = "hugo@toto.com"
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data( constellation, value, expiration)
        
        data = get_constellation_data( constellation)
        self.assert_(data['a'] == value['a'], "not set")

class TrioCase(unittest.TestCase):
    
    
    def test_trio(self):
        CONFIGURATION ="vpc_trio"
        self.constellation_name =  get_unique_short_name("test_%s_" % CONFIGURATION)
        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        
        self.tags = {'TestCase':CONFIGURATION, 
                     'configuration': CONFIGURATION, 
                     'constellation' : self.constellation_name, 
                     'user': self.username,
                     'GMT' : "not avail"}
        
        self.constellation_directory = os.path.abspath( os.path.join(get_test_path('test_trio'), self.constellation_name))
        print("creating: %s" % self.constellation_directory )
        os.makedirs(self.constellation_directory)
        
        launch(self.username, self.constellation_name, self.tags, self.constellation_directory)
        
        sweep_count = 10
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name,  i)
            time.sleep(1)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        terminate(self.username, self.constellation_name, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)
        
