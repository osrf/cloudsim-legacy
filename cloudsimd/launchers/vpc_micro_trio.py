from __future__ import with_statement

import multiprocessing
from common.testing import get_boto_path, get_test_path
import unittest
from common.machine import get_unique_short_name, find_machine,\
    terminate_constellation, create_ec2_proxy
import time
import os
from common import constants

import logging
import boto
from pprint import pprint


def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
    

def get_ec2_instance(ec2conn, id):
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if i.id == id:
            return i
    raise LaunchException("EC2 instance %s does not exist" % id)

def wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, nb_of_tries = 100):
    """
    returns a dictionary of running machine ids indexed by role
    """
    reservations_to_roles = dict((v,k) for k,v in roles_to_reservations.iteritems())
    
    ready_machines = {}
    count = nb_of_tries + len(reservations_to_roles)
    
    while len(reservations_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            print("run count down: %s " % count)
            if count < 0:
                msg = "timeout while waiting for EC2 machine(s) %s" % reservations_to_roles
                raise LaunchException(msg)
            
            for r in ec2conn.get_all_instances():
                reservation = r.id
                if r.id in reservations_to_roles and r.instances[0].state == 'running':
                    role = reservations_to_roles[reservation]
                    aws_id = r.instances[0].id
                    ready_machines[role] =  aws_id
                    reservations_to_roles.pop(reservation)
                    print 'Done launching %s (AWS %s)'%(role, aws_id)
                    done = True
                    break
                
    return ready_machines

def wait_for_multiple_machines_to_terminate(ec2conn, roles_to_aws_ids, nb_of_tries):
    
    ready_machines = {}
    
    count = nb_of_tries + len(roles_to_aws_ids)
    aws_ids_to_roles = dict((v,k) for k,v in roles_to_aws_ids.iteritems())
    
    missing_machines = {}
    for aws_id, role in aws_ids_to_roles.iteritems():
        terminated = ec2conn.terminate_instances(instance_ids=[aws_id] )
        if len(terminated) ==0:
            missing_machines[role] = aws_id
    if len(missing_machines) > 0:    
        msg = "machine(s) %s cannot be terminated" % missing_machines
        raise LaunchException(msg)
    
    while len(aws_ids_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            print("terminate count down: %s " % count)
            if count < 0:
                msg = "timeout while terminating EC2 machine(s) %s" % reservations_to_roles
                raise LaunchException(msg)
            
            reservations =  ec2conn.get_all_instances()
            instances = [i for r in reservations for i in r.instances]
            for instance in instances:
                aws_id = instance.id
                
                if aws_id in aws_ids_to_roles:
                    if instance.state == 'terminated':
                        role = aws_ids_to_roles[aws_id]
                        aws_ids_to_roles.pop(aws_id)
                        print 'Terminated %s (AWS %s)'%(role, aws_id)
                        done = True
                        break


class LaunchException(Exception):
    pass



def launch(username, constellation_name, tags, credentials_ec2, root_directory, machine_name_param = None ):
    
    db_root_dir =os.path.dirname( os.path.dirname(root_directory))
    
    sim_machine_name = "simulator_" + constellation_name
    robot_machine_name = "robot_" + constellation_name
    router_machine_name = "router_" + constellation_name
    
#    from cloudsim import launch as cloudsim_launch
    
    log("team code three")
    
    boto.config = boto.pyami.config.Config(credentials_ec2)
    ec2conn = boto.connect_ec2()
    vpcconn =  boto.connect_vpc()
    
    
    vpc_id = vpcconn.create_vpc('10.0.0.0/24').id
    print("VPC %s" % vpc_id )
    subnet_id = vpcconn.create_subnet(vpc_id, '10.0.0.0/24').id
    
    
    sg_name = 'mysg-%s'%(vpc_id) 
    sg = ec2conn.create_security_group(sg_name, 'Security group for VPC %s'%(vpc_id), vpc_id)
    sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
    sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
    security_group_id = sg.id
    
   
    igw_id = vpcconn.create_internet_gateway().id
    vpcconn.attach_internet_gateway(igw_id, vpc_id)

    route_table_id = vpcconn.create_route_table(vpc_id).id
    vpcconn.create_route(route_table_id, '0.0.0.0/0', igw_id)
    route_table_association_id = vpcconn.associate_route_table(route_table_id, subnet_id)
    elastic_ip = ec2conn.allocate_address('vpc')
    
    eip_public_address = elastic_ip.public_ip
    print("elastic ip %s" % eip_public_address)
    eip_allocation_id = elastic_ip.allocation_id
    
    # keys
    key_pair_name = 'key-%s'%(vpc_id)
    key_pair = ec2conn.create_key_pair(key_pair_name)
    key_pair.save(os.getcwd())
    
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
                                         key_name=key_pair_name,
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
                                 key_name=key_pair_name,
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
                                         key_name=key_pair_name,
                                         user_data=SIM_SCRIPT)
    roles_to_reservations['simulation'] = res.id
    
    running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, nb_of_tries = 100)
    
    ec2conn.create_tags([running_machines['router'] ], {'Name':router_machine_name})
    ec2conn.create_tags([running_machines['simulation'] ], {'Name':sim_machine_name})
    ec2conn.create_tags([running_machines['robot'] ], {'Name':robot_machine_name})
    
    router_aws_id = running_machines['router']
    ec2conn.associate_address(router_aws_id, allocation_id = eip_allocation_id)
    
    router_instance =  get_ec2_instance(ec2conn, router_aws_id)
    router_instance.modify_attribute('sourceDestCheck', False)
    
    data = {'machines': running_machines,
            'security_group_id':security_group_id, 
            'eip_allocation_id':eip_allocation_id, 
            'vpc_id': vpc_id, 
            'igw_id':igw_id , 
            'subnet_id':subnet_id , 
            'route_table_association_id':route_table_association_id,
            'route_table_id':route_table_id,
            'key_pair_name':key_pair_name }
    
    
    print("data:")
    pprint(data)
    
    terminate_vpc_micro_trio(username, constellation_name, credentials_ec2, data, root_directory)



    # sim_zip_fname = os.path.join(machine.config.cfg_dir, "%s.zip" % sim_machine.config.uid)
    # router_machine = find_machine(username, constellation_name, router_machine_name )
def terminate_vpc_micro_trio(username, constellation_name, credentials_ec2, resources, root_directory):
    
    boto.config = boto.pyami.config.Config(credentials_ec2)
    
    ec2conn = boto.connect_ec2()
    vpcconn =  boto.connect_vpc()
    

    try:
        route_table_association_id =  resources['route_table_association_id']
        route_table_id =  resources['route_table_id']
        vpcconn.disassociate_route_table(route_table_association_id)
        vpcconn.delete_route(route_table_id, '0.0.0.0/0')
        vpcconn.delete_route_table(route_table_id)
    except Exception, e:
        print("error cleaning up routing table: %s" % e)
    
    try:
        running_machines =  resources['machines']
        wait_for_multiple_machines_to_terminate(ec2conn, running_machines, 100)
        print 'Waiting after killing instances...'
        time.sleep(20.0)
    except Exception, e:
        print ("error killing instances: %s" % e)
        
    
    try:
        key_pair_name =  resources[ 'key_pair_name']
        ec2conn.delete_key_pair(key_pair_name)
    except Exception, e:
        print("error cleaning up key %s: %s" % (key_pair_name, e))
    
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
    


class TrioCase(unittest.TestCase):
    
    
    def test_trio(self):
        
        self.username = "toto@toto.com"
        self.constellation_name =  get_unique_short_name("test_trio_")
       
        self.credentials_ec2  = get_boto_path()
        self.constellation_directory = "../../test_dir"
        self.tags = {'TestCases':'vpc_micro_trio'}
        
        self.root_directory = get_test_path('test_vpn_micro_trio')
        machine_name_param = None
        launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.root_directory, machine_name_param )
        
#        ls = get_machine_tag(self.username, self.constellation_name, self.sim.config.uid, "launch_state")
#        self.assert_(ls == "running", "bad state")
#        
#        ls = get_machine_tag(self.username, self.constellation_name, self.team.config.uid, "launch_state")
#        self.assert_(ls == "running", "bad state")
     
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate()
        
        terminate_constellation(self.username, self.constellation_name, self.credentials_ec2, self.root_directory)
        
    
        
if __name__ == "__main__":
    unittest.main()        