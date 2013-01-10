from __future__ import print_function

import unittest
import os
import time
import boto
import pprint

from common.machine import get_unique_short_name



 
from common.testing import get_boto_path, get_test_path

from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance 
from launch_utils import log
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient




def aws_connect(credentials_ec2):    
    boto.config = boto.pyami.config.Config(credentials_ec2)
    ec2conn = boto.connect_ec2()
    vpcconn =  boto.connect_vpc()    
    return ec2conn, vpcconn

def launch(username, constellation_name, tags, credentials_ec2, constellation_directory, resources ):
    
    ec2conn, vpcconn = aws_connect(credentials_ec2)
    
    
    sim_machine_name = "simulator_" + constellation_name
    robot_machine_name = "robot_" + constellation_name
    router_machine_name = "router_" + constellation_name
    
    log("trio")
    
    
    resources['vpc_id'] = vpcconn.create_vpc('10.0.0.0/24').id
    vpc_id = resources['vpc_id']
    print("VPC %s" % vpc_id )
    
    resources['subnet_id'] = vpcconn.create_subnet(vpc_id, '10.0.0.0/24').id
    subnet_id = resources['subnet_id']
    
    sg_name = 'mysg-%s'%(vpc_id) 
    sg = ec2conn.create_security_group(sg_name, 'Security group for VPC %s'%(vpc_id), vpc_id)
    sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
    sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
    resources['security_group_id'] = sg.id
    
    
    resources['igw_id'] = vpcconn.create_internet_gateway().id
    igw_id = resources['igw_id']
    vpcconn.attach_internet_gateway(igw_id, vpc_id)

    resources['route_table_id'] = vpcconn.create_route_table(vpc_id).id
    vpcconn.create_route(resources['route_table_id'], '0.0.0.0/0', igw_id)
    resources['route_table_association_id'] = vpcconn.associate_route_table(resources['route_table_id'], subnet_id)
    elastic_ip = ec2conn.allocate_address('vpc')
    resources['router_ip'] = elastic_ip.public_ip
    
    print("elastic ip %s" % resources['router_ip'])
    
    resources['eip_allocation_id'] = elastic_ip.allocation_id

    # keys
    resources['router_key_pair_name'] = 'key-router-%s'%(vpc_id)
    key_pair = ec2conn.create_key_pair(resources['router_key_pair_name'])
    key_pair.save(constellation_directory)
    
    resources['robot_key_pair_name'] = 'key-robot-%s'%(vpc_id)
    key_pair = ec2conn.create_key_pair(resources['robot_key_pair_name'])
    key_pair.save(constellation_directory)
    
    resources['sim_key_pair_name'] = 'key-sim-%s'%(vpc_id)
    key_pair = ec2conn.create_key_pair(resources['sim_key_pair_name'])
    key_pair.save(constellation_directory)
    
    
    TYPE='t1.micro'
    #IMAGE='ami-0d153248'
    
    IMAGE="ami-137bcf7a"
    
    TS_IP='10.0.0.50'

    OPENVPN_SERVER_IP='11.8.0.1'
    OPENVPN_CLIENT_IP='11.8.0.2'
    
    ROUTER_SCRIPT = """#!/bin/bash
exec >/tmp/log 2>&1
apt-get install -y openvpn
cat <<DELIM > /etc/openvpn/openvpn.conf
dev tun
ifconfig %s %s
secret static.key
DELIM
openvpn --genkey --secret /etc/openvpn/static.key
service openvpn restart
chmod 644 /etc/openvpn/static.key
sysctl -w net.ipv4.ip_forward=1
iptables -A FORWARD -i tun0 -o eth0 -j ACCEPT
iptables -A FORWARD -o tun0 -i eth0 -j ACCEPT
touch /done
"""%(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP)
    
    roles_to_reservations ={}
    
    
    res = ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                         subnet_id=subnet_id,
                                         private_ip_address=TS_IP,
                                         security_group_ids=[sg.id],
                                         key_name=resources['router_key_pair_name'] ,
                                         user_data=ROUTER_SCRIPT)
    roles_to_reservations['router'] = res.id
    
    
    ROBOT_IP='10.0.0.52'
    ROBOT_SCRIPT = """#!/bin/bash

exec >/tmp/log 2>&1
route add %s gw %s
"""%(OPENVPN_CLIENT_IP, TS_IP)

    res = ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                 subnet_id=subnet_id,
                                 private_ip_address=ROBOT_IP,
                                 security_group_ids=[sg.id],
                                 key_name=resources['robot_key_pair_name'] ,
                                 user_data=ROBOT_SCRIPT)
    
    roles_to_reservations['robot'] = res.id
    
    SIM_IP='10.0.0.51'
    SIM_SCRIPT = """#!/bin/bash

exec >/tmp/log 2>&1
route add %s gw %s
"""%(OPENVPN_CLIENT_IP, TS_IP)
    res = ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                         subnet_id=subnet_id,
                                         private_ip_address=SIM_IP,
                                         security_group_ids=[sg.id],
                                         key_name=resources['sim_key_pair_name'] ,
                                         user_data=SIM_SCRIPT)
    roles_to_reservations['simulation'] = res.id
    
    running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, nb_of_tries = 150)
    
    resources['router_aws_id'] = running_machines['router']
    resources['robot_aws_id'] = running_machines['robot']
    resources['simulation_aws_id'] = running_machines['simulation']
     
    
    router_tags = {'Name':router_machine_name}
    router_tags.update(tags)
    ec2conn.create_tags([resources['router_aws_id'] ], router_tags)
    
    sim_tags = {'Name':sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([resources['simulation_aws_id'] ], sim_tags)
    
    robot_tags = {'Name':robot_machine_name}
    robot_tags.update(tags)
    ec2conn.create_tags([resources['robot_aws_id'] ], robot_tags)
    
    ec2conn.associate_address(resources['router_aws_id'], allocation_id = resources['eip_allocation_id'])
    
    router_instance =  get_ec2_instance(ec2conn, resources['router_aws_id'])
    router_instance.modify_attribute('sourceDestCheck', False)
    
    
    ssh_router = SshClient(constellation_directory, resources['router_key_pair_name'], 'ubuntu', resources['router_ip'])
    
    done = False
    while not done:
        done = ssh_router.find_file("/done")
        time.sleep(1)
    
    ssh_router.cmd("mkdir cloudsim")
    
    local = os.path.join(constellation_directory, "%s.pem" % resources['robot_key_pair_name'])
    remote = os.path.join("cloudim", "%s.pem" % resources['robot_key_pair_name']) 
    ssh_router.upload_file(local, remote)
    
    local = os.path.join(constellation_directory, "%s.pem" % resources['sim_key_pair_name'])
    remote = os.path.join("cloudim", "%s.pem" % resources['robot_key_pair_name'])
    ssh_router.upload_file(local, remote)
    
    ping_gl = """#!/bin/bash
    
    ssh -i %s ubuntu@%s "ls -l"
    
    """ % (resources['sim_key_pair_name'], SIM_IP)
    ssh_router.create_file(ping_gl, "cloudsim/ping_gl.sh")
    
    # router setup
    # ssh -i key-vpc-527d3738.pem ubuntu@107.23.183.181 "mkdir cloudsim"
    # scp -i key-vpc-527d3738.pem ./key-vpc-527d3738.pem  ubuntu@107.23.183.181:cloudsim


    print("resources:")
    pprint.pprint(resources)
    
    expiration = None
    set_constellation_data(username, constellation_name, resources, expiration)
    



def terminate_vpc_micro_trio(username, constellation_name, credentials_ec2, root_directory):

    ec2conn, vpcconn = aws_connect(credentials_ec2)    
 
    resources = get_constellation_data(username,  constellation_name)
    print("resources:")
    pprint.pprint(resources)
    
    
    try:
        route_table_association_id =  resources['route_table_association_id']
        route_table_id =  resources['route_table_id']
        vpcconn.disassociate_route_table(route_table_association_id)
        vpcconn.delete_route(route_table_id, '0.0.0.0/0')
        vpcconn.delete_route_table(route_table_id)
    except Exception, e:
        print("error cleaning up routing table: %s" % e)
    
    try:
        running_machines =  {}
        running_machines['router'] = resources['router_aws_id']
        running_machines['robot'] = resources['robot_aws_id']
        running_machines['simulation'] = resources['simulation_aws_id']
        wait_for_multiple_machines_to_terminate(ec2conn, running_machines, 150)
        print ('Waiting after killing instances...')
        time.sleep(20.0)
    except Exception, e:
        print ("error killing instances: %s" % e)
        
    
    try:
        router_key_pair_name =  resources[ 'router_key_pair_name']
        ec2conn.delete_key_pair(router_key_pair_name)
    except Exception, e:
        print("error cleaning up router key %s: %s" % (router_key_pair_name, e))
    
    try:
        robot_key_pair_name =  resources[ 'robot_key_pair_name']
        ec2conn.delete_key_pair(robot_key_pair_name)
    except Exception, e:
        print("error cleaning up robot key %s: %s" % (robot_key_pair_name, e))
        
    try:
        sim_key_pair_name =  resources[ 'sim_key_pair_name']
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception, e:
        print("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))
        
    try:    
        security_group_id =  resources['security_group_id' ]
        ec2conn.delete_security_group(group_id = security_group_id)
    except Exception, e:
        print("error cleaning up security group %s: %s" % (security_group_id, e))
    
    try:
        eip_allocation_id =  resources['eip_allocation_id' ]
        ec2conn.release_address(allocation_id = eip_allocation_id)
    except Exception, e:
        print("error cleaning up elastic ip: %s" % e)
    
    try:
        igw_id  =  resources['igw_id']
        vpc_id =  resources['vpc_id']
        vpcconn.detach_internet_gateway(igw_id, vpc_id)
        vpcconn.delete_internet_gateway(igw_id)
    except Exception, e:
        print("error cleaning up internet gateway: %s" % e)
    
    try:
        subnet_id  =  resources['subnet_id']
        vpcconn.delete_subnet(subnet_id)
    except Exception, e:
        print("error cleaning up subnet: %s" % e) 
        
    
    try:
        vpc_id =  resources['vpc_id']
        vpcconn.delete_vpc(vpc_id)
    except Exception, e:
        print("error cleaning up vpc: %s" % e )
    




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
        
        self.constellation_name =  get_unique_short_name("test_trio_")
        
        self.username = "toto@toto.com"
        self.credentials_ec2  = get_boto_path()
        self.tags = {'TestCase':'vpc_micro_trio', 'constellation' : self.constellation_name, 'user': self.username}
        
        self.root_directory = os.path.join(get_test_path('test_vpn_micro_trio'), self.constellation_name,)
        os.makedirs(self.root_directory)
        
        self.resources = {}
        try:
            launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.root_directory, self.resources )
        finally:
            expiration = 3600 * 24
            set_constellation_data(self.username, self.constellation_name, self.resources, expiration)

    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        
        # self.constellation_name = 
        
        terminate_vpc_micro_trio(self.username, self.constellation_name, self.credentials_ec2, self.root_directory)
        
        
    
        
if __name__ == "__main__":
    unittest.main()        