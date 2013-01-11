import time
import os

import logging
import boto
from pprint import pprint
import json
import subprocess
import commands


def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launch", msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
    


class LaunchException(Exception):
    pass


class SshClientException(Exception):
    pass

class SshClient(object):
    def __init__(self, constellation_directory, key_name, username, ip, ):
        self.key_fname = os.path.join(constellation_directory, "%s.pem" % key_name) 
        self.user = '%s@%s' % (username, ip)
        self.ssh_connect_timeout = 1
        
        
    def cmd(self, cmd, extra_ssh_args=[] ): 
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', self.key_fname] + extra_ssh_args + [self.user]
        ssh_cmd.append(cmd)
        log(" ".join(ssh_cmd) )
        po = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode != 0:
            raise SshClientException(out + err)
        else:
            return out
    
    def upload_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 
                   'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', 
                   self.key_fname] + extra_scp_args + [local_fname,'%s:%s'%(self.user, remote_fname)]
        scp_cmd_string = ' '.join(scp_cmd)
        log(scp_cmd_string)
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise SshClientException('scp failed: %s'%(output))
        else:
            return output
    
    def create_file(self, text, remote_fname):
        cmd = "cat <<DELIM > %s\n%s\nDELIM\n" % (remote_fname, text)
        self.cmd(cmd)
    
    def download_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 
                   'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', 
                   self.key_fname] + extra_scp_args + ['%s:%s'%(self.config.user, remote_fname), local_fname ]
        scp_cmd_string = ' '.join(scp_cmd)
        
        log(scp_cmd_string) 
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise SshClientException('scp failed: %s'%(output))
        else:
            return output
        
    def find_file(self, remote_path):
        cmd = 'ls %s' %  remote_path
        try:
            self.cmd(cmd)
        except SshClientException:
            return False
        return True
        

def get_ec2_instance(ec2conn, id):
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if i.id == id:
            return i
    raise LaunchException("EC2 instance %s does not exist" % id)

def wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, nb_of_tries = 150):
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

def wait_for_ssh(self, public_ip, key_file, fname='/done', username = 'ubuntu'):
    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no',
           '-i', '%s.pem'%(key_file), '%s@%s'%(username,
           public_ip), 'ls %s' % fname]
    while True:
        po = subprocess.Popen(ssh_cmd)
        po.communicate()
        if po.returncode == 0:
            break


def _domain(user_or_domain):
    domain = user_or_domain
    if user_or_domain.find('@') > 0:
        domain = user_or_domain.split('@')[1]
    return domain

def set_constellation_data(user_or_domain, constellation, value, expiration = None):
    try:
        import redis
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/" + constellation
        
        str = json.dumps(value)
        red.set(redis_key, str)
        if expiration:
            red.expire(redis_key, expiration)
    except Exception, e:
        log("can't set constellation data: %s" % e)
        

def get_constellation_data(user_or_domain, constellation):
    try:
        import redis
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/"+constellation
        str = red.get(redis_key)
        data = json.loads(str)
        return data
    except:
        return None    


def wait_for_multiple_machines_to_terminate(ec2conn, roles_to_aws_ids, nb_of_tries):
    
     
    
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
            log("terminate count down: %s " % count)
            if count < 0:
                msg = "timeout while terminating EC2 machine(s) %s" % aws_ids_to_roles
                raise LaunchException(msg)
            
            reservations =  ec2conn.get_all_instances()
            instances = [i for r in reservations for i in r.instances]
            for instance in instances:
                aws_id = instance.id
                
                if aws_id in aws_ids_to_roles:
                    if instance.state == 'terminated':
                        role = aws_ids_to_roles[aws_id]
                        aws_ids_to_roles.pop(aws_id)
                        log('Terminated %s (AWS %s)'%(role, aws_id) )
                        done = True
                        break