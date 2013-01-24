from __future__ import print_function

import unittest
import os
import time
import commands


import boto
from boto.pyami.config import Config as BotoConfig

from launch_utils import get_unique_short_name
from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance 
from launch_utils import log
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient
from launch_utils import get_ssh_cmd_generator, empty_ssh_queue # task_list
from launch_utils import ConstellationState # launch_db
from launch_utils.launch_events import latency_event, launch_event, gl_event,\
    simulator_event, machine_state_event
from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_drc_startup_script,\
    get_vpc_router_script, get_vpc_open_vpn, create_openvpn_client_cfg_file,\
    create_vpn_connect_file, create_ros_connect_file, create_ssh_connect_file

from launch_utils.testing import get_boto_path, get_test_path
import zipfile
from shutil import copyfile

CONFIGURATION = "vpc_trio"

ROBOT_IP='10.0.0.52'
TS_IP='10.0.0.50'
SIM_IP='10.0.0.51'

OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'


def aws_connect(credentials_ec2):    
    boto.config = BotoConfig(credentials_ec2)
    # boto.config = boto.pyami.config.Config(credentials_ec2)
    ec2conn = boto.connect_ec2()
    vpcconn =  boto.connect_vpc()    
    return ec2conn, vpcconn

def get_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)

def create_securtity_group(ec2conn, sg_name, constellation_name, vpc_id):
    sg = ec2conn.create_security_group(sg_name, 'Security group for constellation %s' % (constellation_name), vpc_id)
    sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
    sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
    return sg.id


    
machine_states = [ 'terminated', 'terminating', 'stopped' 'stopping', 'nothing', 'starting', 'booting','network_setup', 'packages_setup', 'running', 'simulation_running']
constellation_states = ['terminated', 'terminating','launching', 'running']


def get_aws_states(ec2conn, machine_names_to_ids):
    

    aws_states = {}
    
    ids_to_machine_names = dict((v,k) for k,v in machine_names_to_ids.iteritems())
    
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for instance in instances:
        aws_is = instance.id
        if aws_is in ids_to_machine_names:
            state = instance.state
            machine = ids_to_machine_names[aws_is]
            aws_states[machine] = state
            
    return aws_states

   

def start_simulator(username, constellation_name, machine_name, package_name, launch_file_name, launch_args, ):
    
    constellation_dict = get_constellation_data(username,  constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_key_pair_name    = constellation_dict['router_key_pair_name']
    router_ip    = constellation_dict['router_ip']
    
    try:
        cmd = "bash cloudsim/start_sim.bash " + package_name + " " + launch_args
        ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
        r = ssh_router.cmd(cmd)
        log('start_simulator %s' % r)
    except Exception, e:
        log('start_simulator error %s' % e)
        
        

def stop_simulator(username, constellation_name, machine_name):
    
    constellation_dict = get_constellation_data(username,  constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_key_pair_name    = constellation_dict['router_key_pair_name']
    router_ip    = constellation_dict['router_ip']
    
    try:
        cmd = "bash cloudsim/stop_sim.bash"
        ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
        r = ssh_router.cmd(cmd)
        log('stop_simulator %s' % r)
    except Exception, e:
        log('stop_simulator error %s' % e)

def monitor(username, constellation_name, credentials_ec2, counter):
    
    time.sleep(1)
    constellation = ConstellationState(username, constellation_name)
    
    constellation_state = None
    try:
        
        constellation_state = constellation.get_value("constellation_state") 
        # log("constellation %s state %s" % (constellation_name, constellation_state) )
        if constellation_state == "terminated":
            log("constellation_state terminated for  %s " % constellation_name)
            router_machine_name = constellation.get_value('router_machine_name')
            robot_machine_name = constellation.get_value('robot_machine_name')
            sim_machine_name = constellation.get_value('sim_machine_name')
            launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "red", "terminated")
            launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "red", "terminated")
            launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "red", "terminated")
            return True
    except:
        log("Can't access constellation  %s data" % constellation_name)
        return True
    
    router_state = constellation.get_value('router_state')
    robot_state = constellation.get_value('robot_state')
    simulation_state = constellation.get_value('simulation_state')
    
    router_machine_name = constellation.get_value('router_machine_name')
    robot_machine_name = constellation.get_value('robot_machine_name')
    sim_machine_name = constellation.get_value('sim_machine_name')

    if constellation_state == "terminating":
        launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "terminating")
        launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "orange", "terminating")
        launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", "terminating")

    
    constellation_directory = constellation.get_value('constellation_directory')
    
    router_state_index = machine_states.index(router_state)
    aws_ids = {}
    if constellation.has_value('router_aws_id'):
        aws_ids["router"] = constellation.get_value('router_aws_id')
    if constellation.has_value('robot_aws_id'):
        aws_ids["robot"] = constellation.get_value('robot_aws_id')
    if constellation.has_value('simulation_aws_id'):
        aws_ids["sim"] = constellation.get_value('simulation_aws_id')
    
    
    if len(aws_ids):
        
        ec2conn = aws_connect(credentials_ec2)[0]
        aws_states = get_aws_states(ec2conn, aws_ids)
        
        constellation.set_value("router_aws_state", aws_states["router"]) 
        constellation.set_value("simulation_aws_state", aws_states["sim"])
        constellation.set_value("robot_aws_state", aws_states["robot"])
        gmt = constellation.get_value('gmt')
        
        # todo: is download ready
        machine_state_event(username, CONFIGURATION, constellation_name, robot_machine_name, {'state': aws_states["robot"], 'ip':ROBOT_IP, 'aws_id': aws_ids["router"], 'gmt':gmt, 'username': username, 'key_download_ready':True  })
        machine_state_event(username, CONFIGURATION, constellation_name, sim_machine_name, {'state': aws_states["sim"], 'ip':SIM_IP, 'aws_id': aws_ids["router"], 'gmt':gmt, 'username': username, 'key_download_ready':True  })
        
        router_ip = "xxx.xxx.xxx.xxx"
        if constellation.has_value('router_ip'):
            router_ip =  constellation.get_value('router_ip')
        machine_state_event(username, CONFIGURATION, constellation_name, router_machine_name, {'state': aws_states["router"], 'ip':router_ip, 'aws_id': aws_ids["router"], 'gmt':gmt, 'username': username, 'key_download_ready':True } )
        

    if router_state_index >= machine_states.index('packages_setup'):
        router_ip = constellation.get_value('router_ip')
        router_key_pair_name = constellation.get_value('router_key_pair_name')
        ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
        
        ping_robot = ssh_router.cmd("ping -c3 %s" % ROBOT_IP)
        mini, avg, maxi, mdev = get_ping_data(ping_robot)
        log('ping robot %s %s %s %s' % (mini, avg, maxi, mdev) )
        latency_event(username, CONFIGURATION, constellation_name, robot_machine_name, mini, avg, maxi, mdev)
        
        ping_simulator = ssh_router.cmd("ping -c3 %s" % SIM_IP)
        mini, avg, maxi, mdev = get_ping_data(ping_simulator)
        log('ping simulator %s %s %s %s' % (mini, avg, maxi, mdev) )
        latency_event(username, CONFIGURATION, constellation_name, sim_machine_name, mini, avg, maxi, mdev)
        
        o, ping_router = commands.getstatusoutput("ping -c3 %s" % router_ip)
        if o == 0:
            mini, avg, maxi, mdev = get_ping_data(ping_router)
            log('ping router %s %s %s %s' % (mini, avg, maxi, mdev) )
            latency_event(username, CONFIGURATION, constellation_name, router_machine_name, mini, avg, maxi, mdev)
        
        if constellation_state == "running":
            if router_state == "running":
                launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "blue", "complete")
            
            if robot_state == "running":
                launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "blue", "complete")
            
            if simulation_state == "running":
                launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "blue", "complete")
        
        if router_state == 'packages_setup':
            try:
                router_package = ssh_router.cmd("bash cloudsim/dpkg_log_router.bash")
                #log("cloudsim/dpkg_log_router.bash = %s" % router_package )
                launch_event(username, "vpc_trio", constellation_name, router_machine_name, "orange", router_package)
            except Exception, e:
                log("monitor: cloudsim/dpkg_log_router.bash error: %s" % e)
       
        if robot_state == 'packages_setup':
            try:
                robot_package = ssh_router.cmd("bash cloudsim/dpkg_log_robot.bash")
                #log("cloudsim/dpkg_log_robot.bash = %s" % robot_package )
                launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "orange", robot_package)
            except Exception, e:
                log("monitor: cloudsim/dpkg_log_robot.bash error: %s" % e)
        
        if simulation_state == 'packages_setup':
            try:
                simulation_package = ssh_router.cmd("bash cloudsim/dpkg_log_sim.bash")
                #log("cloudsim/dpkg_log_sim.bash = %s" % simulation_package )
                launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", simulation_package)
            except Exception, e:
                log("monitor: cloudsim/dpkg_log_sim.bash error: %s" % e )
        
        if simulation_state == 'running':
            try:
                ping_gl = ssh_router.cmd("bash cloudsim/ping_gl.bash")
                log("cloudsim/ping_gl.bash = %s" % ping_gl )
                gl_event(username, CONFIGURATION, constellation_name, sim_machine_name, "blue", "running")
                
            except Exception, e:
                gl_event(username, CONFIGURATION, constellation_name, sim_machine_name, "red", "%s" % e)
                log("monitor: cloudsim/ping_gl.bash error %s" % e )
            
            try:
                ping_gazebo = ssh_router.cmd("bash cloudsim/ping_gazebo.bash")
                log("cloudsim/ping_gazebo.bash = %s" % ping_gazebo )
                simulator_event(username, CONFIGURATION, constellation_name, sim_machine_name, ping_gazebo)
            except Exception, e:
                log("monitor: cloudsim/ping_gazebo.bash error: %s" % e )
    
    #log("monitor not done")
    return False


def configurable_launch(username, 
                        constellation_name, 
                        tags, 
                        credentials_ec2, 
                        constellation_directory, 
                        
                        ROUTER_AWS_TYPE,
                        ROUTER_AWS_IMAGE,
                        ROUTER_SCRIPT,
                        
                        ROBOT_AWS_TYPE,
                        ROBOT_AWS_IMAGE,
                        ROBOT_SCRIPT,
                        
                        SIM_AWS_IMAGE,
                        SIM_AWS_TYPE,
                        SIM_SCRIPT                        
                        
                        ):

    log("new trio constellation: %s" % constellation_name) 
       
    ec2conn, vpcconn = aws_connect(credentials_ec2)
    constellation = ConstellationState(username, constellation_name)
    
    constellation.set_value('configuration', CONFIGURATION)
    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('router_state', 'nothing')
    constellation.set_value('robot_state', 'nothing')
    constellation.set_value('simulation_state', 'nothing')
    constellation.set_value('gmt', tags['GMT'])
    constellation.set_value('router_aws_state', 'nothing')
    constellation.set_value('robot_aws_state', 'nothing')
    constellation.set_value('simulation_aws_state', 'nothing')
    constellation.set_value('constellation_directory', constellation_directory)
    
    constellation.set_value('username', username)
    sim_machine_name = "simulator_"+ constellation_name
    constellation.set_value('sim_machine_name', sim_machine_name)
    
    robot_machine_name = "field_computer_"+ constellation_name
    constellation.set_value('robot_machine_name', robot_machine_name)
    
    router_machine_name =  "router_" + constellation_name
    constellation.set_value('router_machine_name', router_machine_name)

    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "???")    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "starting")
    launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "yellow", "starting")
    launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "yellow", "starting")
    
    
#   monitor(username, constellation_name, credentials_ec2, constellation_directory )
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "acquiring public ip")
    
    try:
        router_elastic_ip = ec2conn.allocate_address('vpc')
        router_eip_allocation_id = router_elastic_ip.allocation_id
        constellation.set_value('router_eip_allocation_id', router_eip_allocation_id)
        router_ip = router_elastic_ip.public_ip
        constellation.set_value('router_ip', router_ip)
        log("router elastic ip %s" % router_elastic_ip.public_ip)
        clean_local_ssh_key_entry(router_ip)
    except Exception, e:
        launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "red", "%s" % e)
        raise

    try:
        robot_elastic_ip = ec2conn.allocate_address('vpc')
        robot_eip_allocation_id = robot_elastic_ip.allocation_id
        constellation.set_value('robot_eip_allocation_id', robot_eip_allocation_id)
        robot_public_ip = robot_elastic_ip.public_ip
        constellation.set_value('robot_public_ip', robot_public_ip)
        log("robot elastic ip %s" % robot_elastic_ip.public_ip)
        # clean_local_ssh_key_entry(robot_public_ip)
    except:
        launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "red", "%s" % e)
        
        raise
    
    try:
        sim_elastic_ip = ec2conn.allocate_address('vpc')
        sim_eip_allocation_id = sim_elastic_ip.allocation_id
        constellation.set_value('sim_eip_allocation_id', sim_eip_allocation_id)
        sim_public_ip = sim_elastic_ip.public_ip
        constellation.set_value('sim_public_ip', sim_public_ip)
        log("sim elastic ip %s" % sim_elastic_ip.public_ip)        
    except Exception, e:
        launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "red", "%s" % e)
        raise
        
    # clean_local_ssh_key_entry(router_ip)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "creating virtual private network")
    vpc_id = vpcconn.create_vpc('10.0.0.0/24').id
    constellation.set_value('vpc_id',vpc_id)
    log("VPC %s" % vpc_id )
    availability_zone = boto.config.get('Boto','ec2_region_name')
    subnet_id= vpcconn.create_subnet(vpc_id, '10.0.0.0/24', availability_zone = availability_zone ).id
    constellation.set_value('subnet_id', subnet_id) 

    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "setting up security groups")
    router_sg_name = 'router-sg-%s'%(constellation_name) 
    router_security_group_id = create_securtity_group(ec2conn, router_sg_name, constellation_name, vpc_id)
    constellation.set_value('router_security_group_id', router_security_group_id)

    robot_sg_name = 'robot-sg-%s'%(constellation_name) 
    robot_security_group_id = create_securtity_group(ec2conn, robot_sg_name, constellation_name, vpc_id)
    constellation.set_value('robot_security_group_id', robot_security_group_id)
    
    sim_sg_name = 'sim-sg-%s'%(constellation_name) 
    sim_security_group_id = create_securtity_group(ec2conn, sim_sg_name, constellation_name, vpc_id)
    constellation.set_value('sim_security_group_id', sim_security_group_id)
                            
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "setting up internet gateway")
    igw_id = vpcconn.create_internet_gateway().id
    constellation.set_value('igw_id', igw_id)
    vpcconn.attach_internet_gateway(igw_id, vpc_id)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "creating routing tables")
    route_table_id = vpcconn.create_route_table(vpc_id).id
    constellation.set_value('route_table_id',route_table_id )
    
    vpcconn.create_route(route_table_id, '0.0.0.0/0', igw_id)
    route_table_association_id = vpcconn.associate_route_table(route_table_id, subnet_id)
    constellation.set_value('route_table_association_id', route_table_association_id )  

    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "creating routing tables")
    router_key_pair_name = 'key-router-%s'%(constellation_name)
    constellation.set_value('router_key_pair_name', router_key_pair_name)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "creating ssh keys")
    key_pair = ec2conn.create_key_pair(router_key_pair_name)
    key_pair.save(constellation_directory)
    
    robot_key_pair_name = 'key-robot-%s'%(constellation_name)
    constellation.set_value('robot_key_pair_name', robot_key_pair_name)
    key_pair = ec2conn.create_key_pair(robot_key_pair_name)
    key_pair.save(constellation_directory)
    
    sim_key_pair_name = 'key-sim-%s'%(constellation_name)
    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    
    key_pair = ec2conn.create_key_pair(sim_key_pair_name)
    key_pair.save(constellation_directory)
    
    roles_to_reservations ={}    
    
    try:
        launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "orange", "booting")
        res = ec2conn.run_instances(ROBOT_AWS_IMAGE, instance_type=ROBOT_AWS_TYPE,
                                     subnet_id=subnet_id,
                                 private_ip_address=ROBOT_IP,
                                 security_group_ids=[robot_security_group_id],
                                 key_name=robot_key_pair_name,
                                 user_data=ROBOT_SCRIPT)
        roles_to_reservations['robot_state'] = res.id
    except Exception, e:
        launch_event(username, CONFIGURATION, constellation_name, robot_machine_name, "red", "%s" % e)
        raise       

    
    try:
        launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", "booting")
        res = ec2conn.run_instances(SIM_AWS_IMAGE, instance_type=SIM_AWS_TYPE,
                                         subnet_id=subnet_id,
                                         private_ip_address=SIM_IP,
                                         security_group_ids=[sim_security_group_id],
                                         key_name=sim_key_pair_name ,
                                         user_data=SIM_SCRIPT)
        roles_to_reservations['simulation_state'] = res.id
    except Exception, e:
        launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "red", "%s" % e)
        raise       


    
    try:
        launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "booting")
        res = ec2conn.run_instances(ROUTER_AWS_IMAGE, instance_type=ROUTER_AWS_TYPE,
                                             subnet_id=subnet_id,
                                             private_ip_address=TS_IP,
                                             security_group_ids=[router_security_group_id ],
                                             key_name= router_key_pair_name ,
                                             user_data=ROUTER_SCRIPT)
        roles_to_reservations['router_state'] = res.id
    except Exception, e:
        launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "red", "%s" % e)
        raise     
    
    running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries = 500, final_state = 'network_setup')
    
    #monitor_constellation(username, constellation_name, credentials_ec2, constellation_directory )
    
    router_aws_id =  running_machines['router_state']
    constellation.set_value('router_aws_id', router_aws_id)
    
    robot_aws_id =  running_machines['robot_state']
    constellation.set_value('robot_aws_id', robot_aws_id)
    
    simulation_aws_id =  running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "setting machine tags")
    router_tags = {'Name':router_machine_name}
    router_tags.update(tags)
    ec2conn.create_tags([router_aws_id ], router_tags)
    
    sim_tags = {'Name':sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([ simulation_aws_id ], sim_tags)
    
    robot_tags = {'Name':robot_machine_name}
    robot_tags.update(tags)
    ec2conn.create_tags([ robot_aws_id ], robot_tags)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "assigning elastic IPs")
    ec2conn.associate_address(router_aws_id, allocation_id = router_eip_allocation_id)
    ec2conn.associate_address(robot_aws_id, allocation_id = robot_eip_allocation_id)
    ec2conn.associate_address(simulation_aws_id, allocation_id = sim_eip_allocation_id)
    
    router_instance =  get_ec2_instance(ec2conn, router_aws_id)
    router_instance.modify_attribute('sourceDestCheck', False)
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "packages_setup")
    ssh_router = SshClient(constellation_directory, router_key_pair_name, 'ubuntu', router_ip)
    router_setup_done = get_ssh_cmd_generator(ssh_router,"ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "router_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([router_setup_done], sleep=2)
    
    
    local = os.path.join(constellation_directory, "%s.pem" %  sim_key_pair_name )
    remote = os.path.join("cloudsim", "%s.pem" %  sim_key_pair_name ) 
    ssh_router.upload_file(local, remote)
    
    local = os.path.join(constellation_directory, "%s.pem" % robot_key_pair_name)
    remote = os.path.join("cloudsim", "%s.pem" % robot_key_pair_name)
    ssh_router.upload_file(local, remote)
    
    dpkg_log_robot = """
    #!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "tail -1 /var/log/dpkg.log"
    
    """ % ( robot_key_pair_name, ROBOT_IP)
    ssh_router.create_file(dpkg_log_robot, "cloudsim/dpkg_log_robot.bash")

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
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "DISPLAY=localhost:0 timeout 3 glxinfo"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(ping_gl, "cloudsim/ping_gl.bash")
    
    ping_gazebo = """#!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "gztopic list"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(ping_gazebo, "cloudsim/ping_gazebo.bash")
    
    stop_sim = """#!/bin/bash
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "killall -INT roslaunch"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(stop_sim, "cloudsim/stop_sim.bash")
    
    start_sim = """#!/bin/bash
    
    
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/%s.pem ubuntu@%s "cloudsim/start_sim $1 $2 $3"
    
    """ % (sim_key_pair_name, SIM_IP)
    ssh_router.create_file(start_sim, "cloudsim/start_sim.bash")


    
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "blue", "creating key zip file")
    # create router.zip
    hostname = router_ip
    
    router_machine_dir = os.path.join(constellation_directory, router_machine_name)
    os.makedirs(router_machine_dir )
    file_content = create_openvpn_client_cfg_file(hostname, client_ip = OPENVPN_CLIENT_IP, server_ip = OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(router_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    
    fname_start_vpn = os.path.join(router_machine_dir , "start_vpn.bash")    
    file_content = create_vpn_connect_file()
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)

    fname_ros = os.path.join(router_machine_dir, "ros.bash")    
    file_content = create_ros_connect_file(openvpn_client_ip=OPENVPN_CLIENT_IP, openvpn_server_ip=OPENVPN_SERVER_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)


    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "orange", "creating zip file bundle")    
    router_key_short_filename = router_key_pair_name + '.pem'
    router_key_path =  os.path.join(router_machine_dir, router_key_short_filename)
    copyfile(os.path.join(constellation_directory, router_key_short_filename), router_key_path)
    
    fname_ssh_sh =  os.path.join(router_machine_dir,'router_ssh.bash')
    file_content = create_ssh_connect_file(router_key_short_filename, router_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)

    router_fname_zip = os.path.join(router_machine_dir, "%s.zip" % router_machine_name)
    
    # wait (if necessary) for openvpn key to have been generated, then
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "waiting for key generation") 
    remote_fname = "/etc/openvpn/static.key"
    router_key_ready = get_ssh_cmd_generator(ssh_router, "ls /etc/openvpn/static.key", "/etc/openvpn/static.key", constellation, "sim_state", 'running' ,max_retries = 100)
    empty_ssh_queue([router_key_ready], sleep=2)
    
    vpnkey_fname = os.path.join(router_machine_dir, "openvpn.key")
    # download it locally for inclusion into the zip file
    
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "yellow", "downloading router vpn key to CloudSim server") 
    ssh_router.download_file(vpnkey_fname, remote_fname) 
    
    #creating zip
    files_to_zip = [ router_key_path, 
                     fname_start_vpn,
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    with zipfile.ZipFile(router_fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(router_machine_name, short_fname)
            fzip.write(fname, zip_name)

    constellation.set_value('router_state', 'running')
    launch_event(username, CONFIGURATION, constellation_name, router_machine_name, "blue", "running")
    
    launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", "creating zip file bundle")

    robot_ssh = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "robot_state", "packages_setup", max_retries = 100)
    sim_ssh = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", "packages_setup", max_retries = 100)
    
    robot_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "robot_state", "running",  max_retries = 500)
    sim_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", "running",max_retries = 500)
    empty_ssh_queue([robot_ssh, sim_ssh, robot_done, sim_done], 1)
    
    launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", "rebooting")
    ssh_router.cmd("bash cloudsim/sim_reboot.bash")
    
    launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, "orange", "rebooting")
    ssh_router.cmd("bash cloudsim/sim_reboot.bash")
    
    robot_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_robot.bash cloudsim/setup/done", "cloudsim/setup/done",  constellation, "robot_state", "running",  max_retries = 500)
    sim_done = get_ssh_cmd_generator(ssh_router,"bash cloudsim/find_file_sim.bash cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", "running",max_retries = 500)
    empty_ssh_queue([robot_ssh, sim_ssh, robot_done, sim_done], 1)

    constellation.set_value('constellation_state', 'running')
    log("provisionning done")

    
def launch(username, constellation_name, tags, credentials_ec2, constellation_directory ):
    ROBOT_AWS_TYPE  = 'cg1.4xlarge'
    ROBOT_AWS_IMAGE = 'ami-98fa58f1' 
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    ROBOT_SCRIPT = get_drc_startup_script(open_vpn_script)
    
    SIM_AWS_TYPE = 'cg1.4xlarge'
    SIM_AWS_IMAGE= 'ami-98fa58f1'
    open_vpn_script = get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script)
    ROUTER_AWS_TYPE='t1.micro'
    ROUTER_AWS_IMAGE="ami-137bcf7a"
    ROUTER_SCRIPT = get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP) 
    # ROBOT_AWS_TYPE  = 't1.micro'
    # ROBOT_AWS_IMAGE = "ami-137bcf7a"
    # ROBOT_SCRIPT = get_micro_robot_script()
    
    # SIM_AWS_TYPE  = 't1.micro'
    # SIM_AWS_IMAGE = "ami-137bcf7a"
    # SIM_SCRIPT = get_micro_sim_script()

    configurable_launch(username, constellation_name, tags, credentials_ec2, constellation_directory,
                        ROUTER_AWS_TYPE,
                        ROUTER_AWS_IMAGE,
                        ROUTER_SCRIPT,
                        
                        ROBOT_AWS_TYPE,
                        ROBOT_AWS_IMAGE,
                        ROBOT_SCRIPT,
                        
                        SIM_AWS_IMAGE,
                        SIM_AWS_TYPE,
                        SIM_SCRIPT)
    
def terminate(username, constellation_name, credentials_ec2, constellation_directory):

    resources = get_constellation_data(username,  constellation_name)
    launch_event(username, CONFIGURATION, constellation_name, resources['sim_machine_name'], "orange", "terminating")
    launch_event(username, CONFIGURATION, constellation_name, resources['router_machine_name'], "orange", "terminating")
    launch_event(username, CONFIGURATION, constellation_name, resources['robot_machine_name'], "orange", "terminating")
    
    ec2conn, vpcconn = aws_connect(credentials_ec2)
     
    constellation = ConstellationState(username, constellation_name)
    constellation.set_value('constellation_state', 'terminating')
    
   

    
    log("terminate_vpc_trio [user=%s, constellation_name=%s" % (username, constellation_name) )
    
    
    #log("resources: %s" %   pprint.pformat(resources) )
    
    try:
        route_table_association_id =  resources['route_table_association_id']
        route_table_id =  resources['route_table_id']
        vpcconn.disassociate_route_table(route_table_association_id)
        vpcconn.delete_route(route_table_id, '0.0.0.0/0')
        vpcconn.delete_route_table(route_table_id)
    except Exception, e:
        log("error cleaning up routing table: %s" % e)
    
    try:
        running_machines =  {}
        running_machines['router_state'] = resources['router_aws_id']
        running_machines['robot_state'] = resources['robot_aws_id']
        running_machines['simulation_state'] = resources['simulation_aws_id']

        wait_for_multiple_machines_to_terminate(ec2conn, 
                                                running_machines, 
                                                constellation, 
                                                max_retries = 150, 
                                                final_state = "terminated")
        
        print ('Waiting after killing instances...')
        time.sleep(20.0)
    except Exception, e:
        log ("error killing instances: %s" % e)
        
    router_key_pair_name = None
    try:
        router_key_pair_name =  resources[ 'router_key_pair_name']
        ec2conn.delete_key_pair(router_key_pair_name)
    except Exception, e:
        log("error cleaning up router key %s: %s" % (router_key_pair_name, e))
        
    robot_key_pair_name = None 
    try:
        robot_key_pair_name = resources[ 'robot_key_pair_name']
        ec2conn.delete_key_pair(robot_key_pair_name)
    except Exception, e:
        log("error cleaning up robot key %s: %s" % (robot_key_pair_name, e))
        
    sim_key_pair_name = None
    try:
        sim_key_pair_name =  resources[ 'sim_key_pair_name']
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception, e:
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))
    
    router_security_group_id = None
    try:
        router_security_group_id =  resources['router_security_group_id' ]
        ec2conn.delete_security_group(group_id = router_security_group_id)
    except Exception, e:
        log("error cleaning up router security group %s: %s" % (router_security_group_id, e))
    
    robot_security_group_id =None
    try:    
        robot_security_group_id =  resources['robot_security_group_id' ]
        ec2conn.delete_security_group(group_id = robot_security_group_id)
    except Exception, e:
        log("error cleaning up robot security group %s: %s" % (robot_security_group_id, e))
        
    sim_security_group_id =  None
    try:
        sim_security_group_id = resources['sim_security_group_id' ]
        ec2conn.delete_security_group(group_id = sim_security_group_id)
    except Exception, e:
        log("error cleaning up sim security group %s: %s" % (sim_security_group_id, e))
               
    router_eip_allocation_id = None
    try:
        router_eip_allocation_id =  resources['router_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = router_eip_allocation_id)
    except Exception, e:
        print("error cleaning up router elastic ip: %s" % e)

    try:
        eip_allocation_id =  resources['robot_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = eip_allocation_id)
    except Exception, e:
        print("error cleaning up robot elastic ip: %s" % e)
    
    try:
        eip_allocation_id =  resources['sim_eip_allocation_id' ]
        ec2conn.release_address(allocation_id = eip_allocation_id)
    except Exception, e:
        print("error cleaning up sim elastic ip: %s" % e)    
            
    try:
        igw_id  =  resources['igw_id']
        vpc_id =  resources['vpc_id']
        vpcconn.detach_internet_gateway(igw_id, vpc_id)
        vpcconn.delete_internet_gateway(igw_id)
    except Exception, e:
        log("error cleaning up internet gateway: %s" % e)
    
    try:
        subnet_id  =  resources['subnet_id']
        vpcconn.delete_subnet(subnet_id)
    except Exception, e:
        log("error cleaning up subnet: %s" % e) 
        
    
    try:
        vpc_id =  resources['vpc_id']
        vpcconn.delete_vpc(vpc_id)
    except Exception, e:
        log("error cleaning up vpc: %s" % e )
    
    constellation.set_value('constellation_state', 'terminated')


class DbCase(unittest.TestCase):
    
    def test_set_get(self):
        
        user_or_domain = "hugo@toto.com"
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data(user_or_domain, constellation, value, expiration)
        
        data = get_constellation_data(user_or_domain, constellation)
        self.assert_(data['a'] == value['a'], "not set")

class TrioCase(unittest.TestCase):
    
    
    def test_trio(self):
        
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
        
        launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.constellation_directory)
        
        sweep_count = 10
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    unittest.main()        