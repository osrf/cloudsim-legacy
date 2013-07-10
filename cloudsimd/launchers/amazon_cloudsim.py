from __future__ import print_function

import unittest
import time

import boto
from boto.pyami.config import Config as BotoConfig

#from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils.startup_scripts import get_cloudsim_startup_script
from launch_utils.launch import LaunchException, aws_connect, get_amazon_amis
from launch_utils.testing import get_test_runner
# from launch_utils.monitoring import constellation_is_terminated,\
#     update_machine_aws_states, get_ssh_client, monitor_cloudsim_ping,\
#     monitor_launch_state


from launch_utils.launch_db import log_msg, ConstellationState
from launch_utils.sshclient import clean_local_ssh_key_entry


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


# def monitor(constellation_name, counter):
#     time.sleep(1)
#     if constellation_is_terminated(constellation_name):
#         return True
#
#     constellation = ConstellationState(constellation_name)
#
#     simulation_state = constellation.get_value('simulation_state')
#     update_machine_aws_states(constellation_name, {'simulation_aws_id':"simulation_aws_state"}) 
#
#     ssh_sim = get_ssh_client(constellation_name, simulation_state,'simulation_ip', 'sim_key_pair_name' )
#
#     monitor_cloudsim_ping(constellation_name, 'simulation_ip', 'simulation_latency')
#     monitor_launch_state(constellation_name, ssh_sim, simulation_state, "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg')
#     return False #log("monitor not done")    


def acquire_aws_server(constellation_name,
                       credentials_ec2,
                       constellation_directory,
                       tags):

    sim_machine_name = "cloudsim_%s" % constellation_name
    sim_key_pair_name = 'key-cs-%s' % constellation_name
    #ec2conn = aws_connect()[0]
    boto.config = BotoConfig(credentials_ec2)
    ec2conn = boto.connect_ec2()
    constellation = ConstellationState(constellation_name)
    constellation.set_value('simulation_launch_msg',
                            "setting up security groups")
    sim_sg_name = 'sim-sg-%s' % (constellation_name)
    log("Creating a security group")
    sim_security_group = ec2conn.create_security_group(sim_sg_name,
        "simulator security group for constellation %s" % constellation_name)
    sim_security_group.authorize('tcp', 80, 80, '0.0.0.0/0') # web
    sim_security_group.authorize('tcp', 22, 22, '0.0.0.0/0') # ssh
    sim_security_group.authorize('icmp', -1, -1, '0.0.0.0/0') # ping
    sim_security_group_id = sim_security_group.id
    log("Security group created")
    constellation.set_value('sim_security_group_id', sim_security_group_id)
    constellation.set_value('simulation_launch_msg', "creating ssh keys")

    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    key_pair = ec2conn.create_key_pair(sim_key_pair_name)
    key_pair.save(constellation_directory)
    amis = get_amazon_amis()
    aws_image = amis['ubuntu_1204_x64']
    SIM_SCRIPT = get_cloudsim_startup_script()
    roles_to_reservations = {}
    try:
        constellation.set_value('simulation_launch_msg', "requesting machine")
        res = ec2conn.run_instances(image_id=aws_image,
            instance_type='t1.micro', 
            #subnet_id      = subnet_id,
            #private_ip_address=SIM_IP,
            security_group_ids=[sim_security_group_id],
            key_name=sim_key_pair_name, 
            user_data=SIM_SCRIPT)
        roles_to_reservations['simulation_state'] = res.id
    except Exception as e:
        constellation.set_value("error", "%s" % e)
        raise

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")
# running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries = 150, final_state = 'network_setup')
    running_machines = {}
    count = 200
    done = False
    color = "yellow"
    while not done:
        log("attempt %s" % count)
        time.sleep(2)
        count -= 1
        for r in ec2conn.get_all_instances():
            if count < 0:
                msg = ("timeout while waiting "
                       "for EC2 machine(s) %s" % sim_machine_name)
                raise LaunchException(msg)
            if r.id == res.id:
                state = r.instances[0].state
                if state == 'running':
                    aws_id = r.instances[0].id
                    running_machines['simulation_state'] = aws_id
                    constellation.set_value('simulation_state', 'network_setup')
                    done = True
                constellation.set_value("simulation_aws_state", state)
    constellation.set_value('simulation_launch_msg', "machine running")
    simulation_aws_id = running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)
    sim_tags = {'Name': sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([simulation_aws_id], sim_tags)
# ec2conn.associate_address(router_aws_id, allocation_id = eip_allocation_id)
    sim_instance = get_ec2_instance(ec2conn, simulation_aws_id)
    sim_ip = sim_instance.ip_address
    clean_local_ssh_key_entry(sim_ip)
    constellation.set_value('simulation_ip', sim_ip)
    return sim_ip, simulation_aws_id


def terminate_aws_server(constellation_name):
    log("terminate AWS CloudSim [constellation_name=%s]" % (constellation_name))
    constellation = ConstellationState(constellation_name)
    ec2conn = None
    try:
        running_machines = {}
        running_machines['simulation_aws_state'] = constellation.get_value('simulation_aws_id')
        ec2conn = aws_connect()[0]
        wait_for_multiple_machines_to_terminate(ec2conn, running_machines,
                                                constellation, max_retries=150)
        constellation.set_value('simulation_state', "terminated")
        constellation.set_value('simulation_launch_msg', "terminated")
        print ('Waiting after killing instances...')
        time.sleep(10.0)
    except Exception as e:
        log("error killing instances: %s" % e)
    try:
        sim_key_pair_name = constellation.get_value('sim_key_pair_name')
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception as e:
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))
    try:
        security_group_id = constellation.get_value('sim_security_group_id')
        ec2conn.delete_security_group(group_id=security_group_id)
    except Exception as e:
        log("error cleaning up sim security group %s: %s" % (security_group_id, e))


class DbCase(unittest.TestCase):

    def test_set_get(self):
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data(constellation, value, expiration)
        data = get_constellation_data(constellation)
        self.assert_(data['a'] == value['a'], "redis db value not set")

if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       
