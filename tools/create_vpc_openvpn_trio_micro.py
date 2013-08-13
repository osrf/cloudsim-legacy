#!/usr/bin/env python

import subprocess
import os
import unittest
import time
import boto
import boto.vpc

USERNAME='ubuntu'
IMAGE='ami-0d153248'
TYPE='t1.micro'
TS_IP='10.0.0.50'
SIM_IP='10.0.0.51'
ROBOT_IP='10.0.0.52'
OPENVPN_SERVER_IP='11.8.0.1'
OPENVPN_CLIENT_IP='11.8.0.2'
SIM_ROBOT_SCRIPT = """#!/bin/bash

exec >/tmp/log 2>&1
route add %s gw %s
"""%(OPENVPN_CLIENT_IP, TS_IP)

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

class Creator():

    def __init__(self, ec2conn, vpcconn):
        self.ec2conn = ec2conn
        self.vpcconn = vpcconn
        self.vpc = None
        self.subnet = None
        self.sg_name = None
        self.sg = None
        self.instances = []
        self.key_name = None
        self.eip = None
        self.igw = None
        self.route_table = None
        self.route_table_association_id = None

    def go(self):
        self.vpc = self.vpcconn.create_vpc('10.0.0.0/24').id
        self.subnet = self.vpcconn.create_subnet(self.vpc, '10.0.0.0/24').id
        self.sg_name = 'mysg-%s'%(self.vpc) 
        self.sg = self.ec2conn.create_security_group(self.sg_name, 'Security group for VPC %s'%(self.vpc), self.vpc)
        self.sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
        self.sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
        self.sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
        self.key_pair_name = 'key-%s'%(self.vpc)
        key_pair = self.ec2conn.create_key_pair(self.key_pair_name)
        key_pair.save(os.getcwd())

        print self.vpc

        # Create the sim and robot machines
        res = self.ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                         subnet_id=self.subnet,
                                         private_ip_address=SIM_IP,
                                         security_group_ids=[self.sg.id],
                                         key_name=self.key_pair_name,
                                         user_data=SIM_ROBOT_SCRIPT)
        print 'Launched %s'%(res.id)
        print 'Waiting for %s'%(res.id)
        done = False
        while not done:
            for r in self.ec2conn.get_all_instances():
                if r.id == res.id:
                    self.instances.append(r.instances[0].id)
                    print 'Done launching %s'%(res.id)
                    done = True
                    break

        res = self.ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                         subnet_id=self.subnet,
                                         private_ip_address=ROBOT_IP,
                                         security_group_ids=[self.sg.id],
                                         key_name=self.key_pair_name,
                                         user_data=SIM_ROBOT_SCRIPT)
        print 'Launched %s'%(res.id)
        print 'Waiting for %s'%(res.id)
        done = False
        while not done:
            for r in self.ec2conn.get_all_instances():
                if r.id == res.id:
                    self.instances.append(r.instances[0].id)
                    print 'Done launching %s'%(res.id)
                    done = True
                    break

        # Create the traffic shaper
        res = self.ec2conn.run_instances(IMAGE, instance_type=TYPE,
                                         subnet_id=self.subnet,
                                         private_ip_address=TS_IP,
                                         security_group_ids=[self.sg.id],
                                         key_name=self.key_pair_name,
                                         user_data=ROUTER_SCRIPT)
        print 'Launched %s'%(res.id)
        print 'Waiting for %s'%(res.id)
        done = False
        router = None
        while not done:
            for r in self.ec2conn.get_all_instances():
                if r.id == res.id and r.instances[0].state == 'running':
                    self.instances.append(r.instances[0].id)
                    router = r.instances[0]
                    print 'Done launching %s'%(res.id)
                    done = True
                    break

        self.igw = self.vpcconn.create_internet_gateway().id
        self.vpcconn.attach_internet_gateway(self.igw, self.vpc)

        self.eip = self.ec2conn.allocate_address('vpc')
        self.ec2conn.associate_address(router.id, allocation_id=self.eip.allocation_id)

        self.route_table = self.vpcconn.create_route_table(self.vpc).id
        self.vpcconn.create_route(self.route_table, '0.0.0.0/0', self.igw)
        self.route_table_association_id = self.vpcconn.associate_route_table(self.route_table, self.subnet)
        router.modify_attribute('sourceDestCheck', False)

    def wait_for_ssh(self, fname='/done'):
	ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no',
		   '-i', '%s.pem'%(self.key_pair_name), '%s@%s'%(USERNAME,
		   self.eip.public_ip), 'ls /done']
        while True:
            po = subprocess.Popen(ssh_cmd)
            po.communicate()
            if po.returncode == 0:
                break

    def write_config_files(self):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', 
                   '-i', '%s.pem'%(self.key_pair_name), '%s@%s:%s'%(USERNAME, self.eip.public_ip, '/etc/openvpn/static.key'), 'static.key']
        po = subprocess.Popen(scp_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = po.communicate()
        if po.returncode != 0:
            raise Exception('Failed to scp key:\n%s\n%s'%(out,err))
        ovcfg = open('openvpn.config', 'w+')
        ovcfg.write('remote %s\ndev tun\nifconfig %s %s\nsecret %s\n'%(self.eip.public_ip, OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP, 'static.key'))
        ovcfg.close()

        route_and_openvpn = open('route_and_openvpn.sh', 'w+')
        route_and_openvpn.write('#!/bin/bash\nsudo route add -net 10.0.0.0 netmask 255.255.255.0 gw %s\nsudo openvpn --config openvpn.config&'%(OPENVPN_SERVER_IP))
        route_and_openvpn.close()

    def cleanup(self):
        # Uncomment to avoid cleaning up (e.g., to try connecting to the
        # machines that were created).
        #return

        if self.route_table_association_id:
            self.vpcconn.disassociate_route_table(self.route_table_association_id)
        if self.route_table:
            self.vpcconn.delete_route(self.route_table, '0.0.0.0/0')
            self.vpcconn.delete_route_table(self.route_table)

        for i in self.instances:
            self.ec2conn.terminate_instances([i])
            print 'Waiting for %s'%(i)
            done = False
            while not done:
                for r in self.ec2conn.get_all_instances():
                    if r.instances[0].id == i and r.instances[0].state == 'terminated':
                        print 'Done killing %s'%(i)
                        done = True
                        break
        # Need to wait a bit after killing the instances before deleting security group
        print 'Waiting after killing instances...'
        time.sleep(20.0)
        if self.eip:
            self.ec2conn.release_address(allocation_id=self.eip.allocation_id)
        if self.igw:
            self.vpcconn.detach_internet_gateway(self.igw, self.vpc)
            self.vpcconn.delete_internet_gateway(self.igw)
        if self.sg_name:
            self.ec2conn.delete_security_group(group_id=self.sg.id)
        if self.subnet:
            self.vpcconn.delete_subnet(self.subnet)
        if self.vpc:
            self.vpcconn.delete_vpc(self.vpc)
        if self.key_name:
            self.ec2conn.delete_key_pair(self.key_pair_name)

class Tester(unittest.TestCase):

    def setUp(self):
        # Using default boto config (e.g., ~/.boto)
        self.c = Creator(boto.connect_ec2(), boto.connect_vpc())

    def tearDown(self):
        self.c.cleanup()

    def test_go(self):
        self.c.go()
        self.c.wait_for_ssh()
        self.c.write_config_files()

if __name__ == '__main__':
    unittest.main()
