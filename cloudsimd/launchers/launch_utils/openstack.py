#!/usr/bin/python
from __future__ import print_function
import os
import time
import sys
import uuid
import unittest
from testing import get_test_runner, get_test_path, get_boto_path,\
    get_test_dir

import novaclient.v1_1.client as nvclient
import novaclient.exceptions
 
def launch(image_id):
    creds = get_nova_creds()
    nova = nvclient.Client(**creds)
    print(image_id)
    #keypair
    keypair_name = "key_" + image_id
    if not nova.keypairs.findall(name="key_"+image_id):
        with open(os.path.expanduser('~/.ssh/id_rsa.pub')) as fpubkey:
            nova.keypairs.create(name=keypair_name, public_key=fpubkey.read())
    #security group
    security_group_name = "security_" + image_id
    security_group = nova.security_groups.create(name=security_group_name,
        description="Security group for " + image_id)
    nova.security_group_rules.create(security_group.id,"TCP",22,22,"0.0.0.0/0")
    nova.security_group_rules.create(security_group.id,"ICMP",-1,-1,"0.0.0.0/0")
    #create instance
    instance_name = "instance_" + image_id
    image = nova.images.find(name="cirros-0.3.1-x86_64-uec")
    flavor = nova.flavors.find(name="m1.tiny")
    instance = nova.servers.create(name=instance_name, image=image,
        flavor=flavor, security_groups=[security_group.name], key_name=keypair_name)
    status = instance.status
    while status == 'BUILD':
        time.sleep(5)
        instance = nova.servers.get(instance.id)
        status = instance.status
    print("status: %s" % status)
    #assign_floating_ip
    instance = nova.servers.get(instance.id)
    flag = 0
    instance_ip=None
    for floating_ip in nova.floating_ips.list():
        if floating_ip.instance_id == None:
            instance.add_floating_ip(floating_ip)
            instance_ip = floating_ip
            flag = 1
            break
    if not flag:
        floating_ip = nova.floating_ips.create()
        instance.add_floating_ip(floating_ip)
        instance_ip = floating_ip
    #return image_name,keypair_name#,security group 

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
        print("asdf")
    


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
