import time
import uuid
import boto
from boto.pyami.config import Config as BotoConfig

from launch_db import get_cloudsim_config
from launch_db import log_msg


class LaunchException(Exception):
    pass


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def aws_connect():
    config = get_cloudsim_config()
    credentials_ec2 = config['boto_path']
    boto.config = BotoConfig(credentials_ec2)
    ec2conn = boto.connect_ec2()
    vpcconn = boto.connect_vpc()
    return ec2conn, vpcconn


def get_amazon_amis():
    """
    AMIs are the Amazon disk images. They have unique ids, and those ids vary
    in different regions
    """
    config =get_cloudsim_config()
    credentials_ec2 = config['boto_path'] 
    boto.config = BotoConfig(credentials_ec2)
    availability_zone = boto.config.get('Boto','ec2_region_name')

    amis = {}
    if availability_zone.startswith('eu-west'):
        amis['ubuntu_1204_x64_cluster'] = 'ami-fc191788'
        amis['ubuntu_1204_x64'] = 'ami-f2191786'
        
    if availability_zone.startswith('us-east'):
        amis['ubuntu_1204_x64_cluster'] = 'ami-98fa58f1'
        amis['ubuntu_1204_x64'] = 'ami-137bcf7a'

    return amis

def get_unique_short_name(prefix = 'x'):
    s = str(uuid.uuid1()).split('-')[0]
    return prefix + s

def get_ec2_instance(ec2conn, id):
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if i.id == id:
            return i
    raise LaunchException("EC2 instance %s does not exist" % id)

def wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries, initial_state = "booting", final_state = "network_setup"):
    """
    returns a dictionary of running machine ids indexed by role
    """
    
    # mark all machines as "booting" (or other initial state)
    for machine_state in roles_to_reservations.keys():
        constellation.set_value(machine_state, initial_state)
    
    reservations_to_roles = dict((v,k) for k,v in roles_to_reservations.iteritems())
    
    ready_machines = {}
    count = max_retries + len(reservations_to_roles)
    
    while len(reservations_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            print("Waiting for running state: %s %s/%s " % (reservations_to_roles.values(), count, max_retries)  )
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
                    # mark this machines as "network_setup" (or other final state)
                    constellation.set_value(role, final_state)
                    print 'Done launching %s (AWS %s)'%(role, aws_id)
                    
                    done = True
                    break
                
    return ready_machines




def wait_for_multiple_machines_to_terminate(ec2conn, roles_to_aws_ids, constellation, max_retries, final_state = "terminated"):
    
    strict = False
    
    count = max_retries + len(roles_to_aws_ids)
    
    aws_ids_to_roles = dict((v,k) for k,v in roles_to_aws_ids.iteritems())
    
    missing_machines = {}
    for aws_id, role in aws_ids_to_roles.iteritems():
        log("terminate %s %s" % (role, aws_id))
        terminated = []
        try:
            terminated = ec2conn.terminate_instances(instance_ids=[aws_id] )
        except Exception, e:
            log("FAILED to terminate  %s %s : %s"  % (role, aws_id, e) )
            
            
        if len(terminated) ==0:
            missing_machines[role] = aws_id
    if len(missing_machines) > 0:    
        msg = "machine(s) %s cannot be terminated" % missing_machines
        if strict:
            raise LaunchException(msg)
    
    # todo: recalc the aws_ids_to_roles without the missing machines
    
    
    while len(aws_ids_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            #log("terminate count down: %s %s/%s " % (aws_ids_to_roles.values(), count, max_retries) )
            if count < 0:
                msg = "timeout while terminating EC2 machine(s) %s" % aws_ids_to_roles
                raise LaunchException(msg)
            
            reservations =  ec2conn.get_all_instances()
            instances = [i for r in reservations for i in r.instances]
            for instance in instances:
                aws_id = instance.id
                
                if aws_id in aws_ids_to_roles:
                    constellation.set_value(role, instance.state)
                    if instance.state == 'terminated':
                        role = aws_ids_to_roles[aws_id]
                        aws_ids_to_roles.pop(aws_id)
                        log('Terminated %s (AWS %s)'%(role, aws_id) )
                        
                        done = True
                        break
                    else:
                        log("%s (AWS %s) state: %s %s/%s" % (role, aws_id,instance.state, count, max_retries ))