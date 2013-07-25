from __future__ import print_function

import os
import time
import sys
import uuid
import unittest
import redis
import paramiko
import commands

import novaclient.v1_1.client as nvclient
import novaclient.exceptions

from testing import get_test_runner, get_test_path, get_boto_path,\
    get_test_dir
from launch_db import ConstellationState
from launch_db import get_unique_short_name
from sshclient import SshClient
from ssh_queue import get_ssh_cmd_generator, empty_ssh_queue

def acquire_openstack_server(constellation_name,
                             creds,
                             machine_name,
                             constellation_directory):
    floating_ip, instance_name, keypair_name, security_group_name = \
        launch(constellation_name, machine_name, constellation_directory)
    constellation = ConstellationState(constellation_name)
    constellation.set_value("security_group", security_group_name)
    constellation.set_value("keypair", keypair_name)
    constellation.set_value("instance", instance_name)
    return floating_ip, instance_name, keypair_name


def terminate_openstack_server(constellation_name):
    #get secgroups and key
    constellation = ConstellationState(constellation_name)
    secgroup = constellation.get_value("security_group")
    keypair = constellation.get_value("keypair")
    instance_name = constellation.get_value("instance")
    terminate(instance_name, keypair, secgroup)


def launch(constellation_name, machine_name, constellation_directory):
    creds = get_nova_creds()
    nova = nvclient.Client(**creds)
    #keypair
    keypair_name = "key_" + constellation_name
    keypair = nova.keypairs.create(name=keypair_name)
    private_key = keypair.private_key
    path = os.path.join(constellation_directory, "%s.pem" % keypair_name)
    with open(path, 'w') as key_file: 
        key_file.write(private_key)
    os.chmod(path, 0600)
    #security group
    security_group_name = "security_" + constellation_name
    security_group = nova.security_groups.create(
        name=security_group_name,
        description="Security group for " + constellation_name)
    nova.security_group_rules.create(
        security_group.id, "TCP", 22, 22, "0.0.0.0/0")
    nova.security_group_rules.create(
        security_group.id, "ICMP", -1, -1, "0.0.0.0/0")
    #create instance
    instance_name = machine_name + "_" + constellation_name
    image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
    flavor = nova.flavors.find(name="m1.tiny")
    user_data = "startup_scripts.py" #startup script
    instance = nova.servers.create(name=instance_name,
                                   image=image,
                                   flavor=flavor,
                                   security_groups=[security_group.name],
                                   key_name=keypair_name,
                                   user_data=user_data)
    status = instance.status
    while status == 'BUILD':
        time.sleep(5)
        instance = nova.servers.get(instance.id)
        status = instance.status
    print("status: %s" % status)
    #assign_floating_ip
    instance = nova.servers.get(instance.id)
    flag = 0
    instance_ip = None
    for floating_ip in nova.floating_ips.list():
        if floating_ip.instance_id is None:
            instance.add_floating_ip(floating_ip)
            flag = 1
            break
    if not flag:
        floating_ip = nova.floating_ips.create()
        instance.add_floating_ip(floating_ip)
    return floating_ip, instance_name, keypair_name, security_group_name


def terminate(instance_name, keypair_name, secgroup_name):
    creds = get_nova_creds()
    nova = nvclient.Client(**creds)
    instance = nova.servers.find(name=instance_name)
    secgroup = nova.security_groups.find(name=secgroup_name)
    #delete security group
    print("Deleting security group")
    instance.remove_security_group(secgroup_name)
    secgroup.delete()
    #delete floating ip(s)
    print("Deleting floating ip")
    associated_ips = nova.floating_ips.findall(instance_id=instance.id)
    for ip in associated_ips:
        nova.floating_ips.delete(ip)
    #delete keypair
    print("Deleting keypair")
    nova.keypairs.find(name=keypair_name).delete()
    #delete instance
    print("Terminating instance")
    terminated = False
    instance.delete()
    while not terminated:
        try:
            nova.servers.find(name=instance_name)
            time.sleep(5)
        except novaclient.exceptions.NotFound:
            print("Instance terminated")
            terminated = True


def get_nova_creds():
    creds = {}
    creds['username'] = os.environ['OS_USERNAME']
    creds['api_key'] = os.environ['OS_PASSWORD']
    creds['auth_url'] = os.environ['OS_AUTH_URL']
    creds['project_id'] = os.environ['OS_TENANT_NAME']
    return creds


class TestOpenstack(unittest.TestCase):
    def test1(self):
        self.constellation_name = get_unique_short_name("x")
        p = os.path.join(get_test_path("openstack"), self.constellation_name)
        self.constellation_directory = os.path.abspath(p)
        print(self.constellation_directory)
        os.makedirs(self.constellation_directory)
        print(self.constellation_directory)
        creds = get_nova_creds()
        machine_name = "cloudsim_server"
        floating_ip, instance_name, keypair_name = acquire_openstack_server(
            self.constellation_name, creds, machine_name,
            self.constellation_directory)
        constellation = ConstellationState(self.constellation_name)
        uname = 'cirros'
        ssh = SshClient(self.constellation_directory, keypair_name,
                'cirros', floating_ip.ip)
        cmd = 'pwd'
        expected_output = '/home/cirros'
        ssh_command = get_ssh_cmd_generator(ssh, cmd, expected_output,
                constellation, "can_ssh", 1, max_retries=100)
        ctr = 30
        done = False
        while not done:
            time.sleep(2)
            ctr -= 1
            if ctr < 0:
                msg = ("timeout while waiting for floating ip for %s" 
                    % sim_machine_name)
            pingable, ping_str = commands.getstatusoutput(
                "ping -c3 %s" % floating_ip.ip)
            if pingable == 0:
                done = True
        empty_ssh_queue([ssh_command], 2)
        self.assertEqual(pingable, 0, ping_str)

    def setUp(self):
        pass

    def tearDown(self):
        terminate_openstack_server(self.constellation_name)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
