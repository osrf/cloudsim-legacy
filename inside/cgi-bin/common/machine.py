from __future__ import with_statement
from __future__ import print_function

import commands
import unittest
import uuid
import os
import sys
import time
import subprocess
import json
import shutil
#import common
 
import boto

from machine_configuration import Machine_configuration

from constants import *
from startup_script_builder import *
import zipfile
from  testing import get_test_runner

"""
Removes the key for this ip, in case we connect to a different machine with the
same key in the future. This avoids ssh messages
"""
def clean_local_ssh_key_entry( hostname):
    www_ssh_host_file = "/var/www/.ssh/known_hosts" 
    if os.path.exists(www_ssh_host_file):
        cmd = 'sudo ssh-keygen -f %s -R %s' % (www_ssh_host_file, hostname)
        s,o = commands.getstatusoutput(cmd)
    
        print("clean_local_ssh_key_entry for %s" % hostname)
        print(o)
        print
        return s
    else:
        return ""

"""
Calls the ping command and returns statistics
"""
def ping(hostname, count=3):
    import re
    s,out = commands.getstatusoutput("ping -c%s %s" % (count, hostname) )
    if s == 0:
        min, avg, max, mdev  =  [float(x) for x in out.split()[-2].split('/')]
        return (min, avg, max, mdev)
    
    raise MachineException(out)


class MachineException(Exception):
    pass

def create_ec2_proxy(boto_config_file):
    boto.config = boto.pyami.config.Config(boto_config_file)
    ec2 = boto.connect_ec2()
    return ec2

class StdoutPublisher(object):
    def __init__(self, username = None):
        self.username = username
        
        
    def event(self, event_data):
        #print("%s = (%s, %s)" %(self.username, name, data) )
        event_str = "event: cloudsim"
        data_str = "data:%s\n\n" %  (event_data)
            
        print(event_str)
        if event_data:
            print(data_str)

        sys.stdout.flush()
        
        
        

#class Constellation(object):
#    def __init__(self, type, name, root_directory):
#        pass
#    
#    def get_path(self):
#        pass
    
    

class Machine (object):
    
    def __init__(   self,
                    unique_name,
                    config, 
                    event,
                    tags ={}, 
                    credentials_ec2 = BOTO_CONFIG_FILE_USEAST, # boto file
                    root_directory = MACHINES_DIR,
                    do_launch = True):
        self.event = event
        self.log = None
        self.config = config
        self.startup_script_done_file = '/tmp/startup_script_done'
        self.ssh_connect_timeout = 1
        # We use this file as an indicator that our startup script has completed successfully
        if do_launch:
            self.config.credentials_ec2 = credentials_ec2
            self.ec2 = create_ec2_proxy(self.config.credentials_ec2 )
            self.config.tags = tags
            self.config.tags['machine_name'] = unique_name
            self.config.uid = unique_name
            self.config.root_directory = root_directory
            self.config.cfg_dir=os.path.join(self.config.root_directory, self.config.uid)
            os.makedirs(self.config.cfg_dir)
            
            self.config.launch_log_fname = os.path.join(self.config.cfg_dir, 'launch.log')
            # self.log = open(self.config.launch_log_fname, 'w')
            self.config.instance_fname = os.path.join(self.config.cfg_dir, 'instance.json')
            
            #self.config.save_json(self.config.instance_fname)
            self._create_machine_keys() 
            # self.config.save_json(self.config.instance_fname)
            
            self._launch()
            
            self.config.save_json(self.config.instance_fname)
            
            #self.log.close()
            #self.log = None
        else:
            self.ec2 = create_ec2_proxy(self.config.credentials_ec2 )

    @classmethod
    def from_file(cls,  fname, event = None):
        if(event == None):
            x = StdoutPublisher()
            event = x.event
        config = Machine_configuration.from_file(fname)
        x = Machine(config.uid, config, event, do_launch = False)
        return x

    def _event(self, data_dict):
        if self.event:
            data_dict.update(self.config.tags)
            self.event(data_dict)
        
    
    def _get_instance(self, reservation_id):
        for r in self.ec2.get_all_instances():
            if r.id == reservation_id and r.instances[0].public_dns_name:
                inst = r.instances[0]
                return inst
        return None
    
    def _launch(self):
        """
        Called by the ctor when launch is True
        """        
        self.config.startup_script += '\ntouch %s\n'%(self.startup_script_done_file)
        try:
            # Start it up
            
            self._event({"type:":"launch", "state":"reserve"})
            res = self.ec2.run_instances(   image_id=self.config.image_id, 
                                            min_count =1,
                                            max_count =1,
                                            key_name=self.config.kp_name,
                                            instance_type=self.config.instance_type,
                                            security_groups = self.config.security_groups,
                                            user_data=self.config.startup_script)
            #self.config.print_cfg()
            self.config.reservation = res.id
            self._event({"type":"launch", "state":"reserve", "reservation_id":'%s'% self.config.reservation } )
            
            self._event({"type": "launch", "state":"waiting_for_ip"})
            retries = self.config.ip_retries
            tries = 0
            while tries< retries:
                done = False
                tries += 1
                self._event({"type":"launch", "state":'retry', "goal":"ip_set", "try":tries, "retries":retries} )
                for r in self.ec2.get_all_instances():
                    if r.id == res.id and r.instances[0].public_dns_name:
                        done = True
                        inst = r.instances[0]
                        self.config.hostname = inst.public_dns_name
                        self.config.ip = inst.ip_address
                        self.config.aws_id = inst.id
                        self._event({"type":"launch", "state":"ip_configured", "ip": self.config.ip, 'aws_id': self.config.aws_id})
                        break
                    time.sleep(0.1)
                if done:
                    break 
                
            if tries >= retries:
                self._event({"type":"launch", "state":"fail", "action":'ip_set'})
                raise MachineException("Can't get IP for machine reservation '%s'" % self.config.reservation)
            if len(self.config.tags):
                self._event({"type": "launch", "state":'tags_set'})
                self.ec2.create_tags([self.config.aws_id], self.config.tags)
                self._event({"launch":"launch", "state":'tags_set'})
            
            
        except Exception as e:
            # Clean up
            
            if os.path.exists(self.config.kp_fname):
                os.unlink(self.config.kp_fname)
            shutil.rmtree(self.config.cfg_dir)
            # re-raise
            raise

    def create_ssh_connect_script(self, fname = "ssh.sh"):
        ssh_connect_fname = os.path.join(self.config.cfg_dir, fname)
        with open(ssh_connect_fname, 'w') as f:
            s = create_ssh_connect_file(self.config.kp_name + '.pem', self.config.ip, self.config.username)
            f.write(s)

    def _create_machine_keys(self):
        # save the ssh key
        kp_name = 'key-%s'%(self.config.uid)
        kp = self.ec2.create_key_pair(kp_name)
        kp.save(self.config.cfg_dir)
        
        self.config.kp_name = kp_name
        self.config.kp_fname = os.path.join(self.config.cfg_dir, self.config.kp_name + '.pem')
    
    def get_user_ssh_command_string(self):
        """
        Returns an ssh command that the user can type to access the machine
        """
        return "ssh -i %s %s@%s"%(self.config.kp_fname, self.config.username, self.config.hostname)

    def ssh_send_command(self, cmd, extra_ssh_args=[]):
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', self.config.kp_fname] + extra_ssh_args + ['%s@%s'%(self.config.username, self.config.hostname)]
        #ssh_cmd.extend([cmd])
        ssh_cmd.append(cmd)
        po = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode != 0:
            raise MachineException(out + err)
        else:
            return out

    def scp_send_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 
                   'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', 
                   self.config.kp_fname] + extra_scp_args + [local_fname,'%s@%s:%s'%(self.config.username, self.config.hostname, remote_fname)]
        scp_cmd_string = ' '.join(scp_cmd)
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise MachineException('scp failed: %s'%(output))
        else:
            return output
        
    def scp_download_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 
                   'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', 
                   self.config.kp_fname] + extra_scp_args + ['%s@%s:%s'%(self.config.username, self.config.hostname, remote_fname), local_fname ]
        scp_cmd_string = ' '.join(scp_cmd)
        print(scp_cmd_string) 
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise MachineException('scp failed: %s'%(output))
        else:
            return output

  
    def ssh_wait_for_ready(self, the_file_to_look_for=None):
        delay = 0.5
        file_to_look_for = the_file_to_look_for
        if not file_to_look_for:
            file_to_look_for = self.startup_script_done_file
        cmd = 'ls %s' %  file_to_look_for
        
        retries = self.config.ssh_retries
        tries = 0
        self._event({"type" :"launch", "state":'ssh_wait_for_ready', "file":file_to_look_for, "try": tries, "retries":retries })
        while tries < retries:
            tries += 1
            # print ( "%s / %s" % (tries, retries))
            self._event({"type":"launch", "state":'retry', "goal":"file_ready", "file": file_to_look_for,  "try": tries, "retries": retries })
            sys.stdout.flush()
            try:
                self.ssh_send_command(cmd)
            except MachineException as ex:
                # Expected; e.g., the machine isn't up yet
                time.sleep(delay)
            else:
                self._event({"type" : "check", "state":'ssh_connected'})
                return
        self._event({"type":"launch", "state": 'fail', 'action':'ssh_connect'})   
        raise MachineException("Maximum retry limit exceeded; ssh connection could not be established or file '%s' not found" % file_to_look_for)
    
    def terminate(self):
        self._event({"type":"launch", "state":'terminated'})
        terminated_list = self.ec2.terminate_instances(instance_ids=[self.config.aws_id])
        if(len(terminated_list) == 0 ):
            self._event({"type":"fail", "state":'terminated', 'machine_id': self.config.aws_id})
            raise MachineException("Could not terminate instance %s" % self.config.aws_id)
        self.ec2.delete_key_pair(self.config.kp_name)
        self._event({"type":"check", "state":'terminated', "machine_id":self.config.aws_id})
        
    
 
    
    def get_X_status(self):
        #self._event({"type":"test", "state":'X, OpenGL'})
        try:
            r = self.ssh_send_command('DISPLAY=localhost:0 glxinfo')
            return True
        except:
            return False

    def ping(self, count = 3):
        #self._event({"type":"test", "state":'latency', 'count':count})
        host = self.config.hostname
        try:
            min, avg, max, mdev = ping(host, count)
            return {'count':count, 'min':min, 'avg':avg, 'max':max, 'mdev':mdev}
        except:
            return None

    def get_gazebo_status(self):
        
        d = self.config.distro
        #cmd = 'source /opt/ros/%s/setup.bash && rosrun gazebo gztopic list' % d
        cmd = 'source /usr/share/gazebo-1.?/setup.sh && gztopic list' 
        
        try:
            r = self.ssh_send_command(cmd)
            
            return True
        except:
            return False

    def get_aws_status(self, timeout=1):
        #self._event({"type":"test", "state":'aws'})

        data = {}
        data.update(self.config.tags)
        
        data['hostname'] = self.config.hostname
        data['ip'] = self.config.ip
        data['aws_id'] = self.config.aws_id
        data['result'] = 'success'
        for r in self.ec2.get_all_instances():
            for i in r.instances:
                if i.id == self.config.aws_id:
                    data[ 'state'] = str(i.state)
                    self._event(data) 
                    return data
        data['state'] = 'does_not_exist'
        data['result'] = 'failure'
        return data
    
    def reboot(self):
        """
        Reboots the machine and waits until it has gone down ()
        """
        #r = self.ec2.reboot_instances([self.config.aws_id])
        r = self.ssh_send_command("sudo reboot")

        while self.ping(1):
            time.sleep(0.1)
        
        return r
        

#    def reboot(self, timeout=1):
#        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'sudo', 'reboot']
#        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
#        out,err = po.communicate()
#        if po.returncode == 0:
#            return (True, out + err)
#        else:
#            return (False, out + err)
#    def stop(self, timeout=1):
#        ec2 = create_ec2_proxy(self.botofile)
#        try:
#            ec2.stop_instances([self.aws_id])
#        except Exception as e:
#            return False, str(e)
#        return True, ''
#
#    def start(self, timeout=1):
#        ec2 = create_ec2_proxy(self.botofile)
#        try:
#            ec2.start_instances([self.aws_id])
#        except Exception as e:
#            return False, str(e)
#        return True, ''

class DomainDb(object):
    
    def __init__(self,  root_dir = MACHINES_DIR):
        print("")
        self.root_dir = root_dir
    
    def get_domains(self):
        domains = []
        if os.path.exists(self.root_dir):
            for domain in os.listdir(self.root_dir):
                domains.append(domain)

        return domains
    
    
        
                


def set_machine_tag(domain, constellation, machine, key, value, expiration = None):
    try:
        import redis
        red = redis.Redis()
        redis_key = domain+"/"+constellation+"/" + machine
        str = red.get(redis_key)
        if not str:
            str = "{}"
        machine_info = json.loads(str)
        machine_info[key] = value
        str2 = json.dumps(machine_info)
        red.set(redis_key, str2)
        if expiration:
            red.expire(redis_key, expiration)
    except:
        pass

def get_machine_tag(domain, constellation, machine, key):
    try:
        import redis
        red = redis.Redis()
        redis_key = domain+"/"+constellation+"/" + machine
        str = red.get(redis_key)
        machine_info = json.loads(str)
        value = machine_info[key]
        return value
    except:
        return None
   

class MachineDb(object):
    
    def __init__(self, email, machine_dir = MACHINES_DIR):
        self.user = email
        self.domain = email.split('@')[1]
        self.root_dir =  os.path.join(machine_dir, self.domain)
        
    def get_machines_in_constellation(self, constellation):
        machines = {}
        if os.path.exists(self.root_dir):
            constellation_path = os.path.join(self.root_dir, constellation)
            constellation_info = self.get_constellation(constellation)
            constellation_info['machines'] = {}
            machine_list = os.listdir(constellation_path)
            machine_list.remove('constellation.json')
            for machine_name in machine_list:
                machine = self.get_machine(constellation, machine_name)
                if machine:
                    machines[machine_name] = machine 
        return machines
    
    def is_machine_up(self, constellation, machine_name):
        r = get_machine_tag(self.domain, constellation, machine_name, "up")
        return r == True # can be None
    
    def get_machines(self, get_all_machines = False):
        machines = {}
        if os.path.exists(self.root_dir):
            for constellation in os.listdir(self.root_dir):
                
                constellation_path = os.path.join(self.root_dir, constellation)
                constellation_info = self.get_constellation(constellation)
                constellation_info['machines'] = {}
                machine_list = os.listdir(constellation_path)
                machine_list.remove('constellation.json')
                machines[constellation] = constellation_info
                for machine_name in machine_list:
                    machine = self.get_machine(constellation, machine_name)
                    if machine:
                        if get_all_machines or self.is_machine_up(constellation, machine_name ):
                            machines[constellation]['machines'][machine_name] = machine 
        return machines
    
    def get_constellation(self, constellation):
        fname =  os.path.join(self.root_dir, constellation, CONSTELLATION_JSONF_NAME)
        constellation_info = None
        with open(fname,'r') as fp:
            str = fp.read()
            constellation_info = json.loads(str)
        return constellation_info
        
        
    def get_machine(self, constellation, machine_name):
        fname =  os.path.join(self.root_dir, constellation, machine_name, 'instance.json')
        if os.path.exists(fname):
            machine = Machine.from_file(fname)
            return machine
        return None
    
    def get_machines_as_json(self):
        d = self.get_machines_as_dict()
        str = json.dumps(d)
        return str
    
    def get_machines_as_dict(self):
        jmachines = {}
        machines = self.get_machines()
        for constellation_name, constellation_info in machines.iteritems():
            
            jmachines[constellation_name] = {}
            jmachines[constellation_name]['config'] = constellation_info['config']
            c_machines = constellation_info['machines']
            
            jmachines[constellation_name] = constellation_info
            for machine_name, machine  in c_machines.iteritems():
                jmachine = {}
                jmachine.update(machine.config.__dict__)
                del(jmachine['startup_script'])
                jmachines[constellation_name]['machines'][machine_name] = jmachine
                
        return jmachines
    
        
#        json_machines ={}
#        for name, machine in machines.iteritems():
#            m = {}
#            m.update(machine.config.__dict__)
#            if (m.has_key("startup_script")):
#                m.pop("startup_script")
#            json_machines[name] = m
#            
#        str = json.dumps(json_machines)
        return str
    
           

    def get_launch_log_fname(self, machine_name):
        fname =  os.path.join(self.root_dir, machine_name, "launch.log")
        return fname
    
    def get_zip_fname(self, constellation_name, machine_name):
        fname = os.path.join(self.root_dir, constellation_name, machine_name, machine_name + ".zip")
        return fname


def list_all_machines_accross_domains(root_dir = MACHINES_DIR):
    
    ddb = DomainDb(root_dir)
    domains = ddb.get_domains()
    
    all_machines = []
    for domain in domains:
        email = "user@" + domain
        mdb = MachineDb(email, root_dir)
        machines = mdb.get_machines()
        for constellation_name, constellation in machines.iteritems():
            for machine_name, machine in constellation['machines'].iteritems():
                all_machines.append( (domain, constellation, machine)  )
    return all_machines

#########################################################################


class PingTest(unittest.TestCase):
    
    def test_a_ping(self):
         pass
#        print( "ping google.com 3x: (min, avg, max, mdev)")
#        min, avg, max, mdev  = ping("google.com", 3)
#        print ("min, avg, max, mdev\n", min, avg, max, mdev)
#        self.assert_(max > min, "bad pong")
#        self.assert_(min > 1.0, "bad pong")
#        
#        caught = False
#        try:
#            r = ping("xYZ_google_XYZ.com", 3)
#        except MachineException, e:
#            caught = True
#            print(e)
#        
#        self.assert_(caught)
        
             
class MachineCaseVpn(object): #(unittest.TestCase): 

    def get_boto_path(self):
        return "/home/hugo/code/boto.ini"


        
    def test_micro_launch_vpn_1(self):
        
        root_directory = "test_launch_vpn"
        publisher = StdoutPublisher("toto@toto.com")
        machine_name = str(uuid.uuid1())
        
        cmd = "rm -rf %s" % root_directory
        status, o = commands.getstatusoutput(cmd)
        print(o)
        
        
        startup_script = """#!/bin/bash
# Exit on error
set -e

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
      
        file_content = create_openvpn_server_cfg_file()
        startup_script += inject_file_into_script("openvpn.config",file_content)

        startup_script += INSTALL_VPN
        print(startup_script)

        tags = {'hello':'world', 'user':'toto@toto.com'}
                   
        config = Machine_configuration()
        config.initialize(   image_id ="ami-137bcf7a", 
                             instance_type = 't1.micro', # 'm1.small' , 
                             security_groups = ['ping_ssh'],
                             username = 'ubuntu', 
                             distro = 'precise',
                             startup_script = startup_script,
                             ip_retries=100, 
                             ssh_retries=200)

        micro = Machine(machine_name,
                         config,
                         publisher.event,
                         tags,
                         credentials_ec2 =  self.get_boto_path(), # boto file
                         root_directory = root_directory)
        
        micro.create_ssh_connect_script()
        clean_local_ssh_key_entry(micro.config.ip )
        print("")
        print("")
        print("Waiting for ssh")
        micro.ssh_wait_for_ready("/home/ubuntu")
        
        print("Waiting for setup to complete")
        micro.ssh_wait_for_ready()
        
        print("Downloading key")
        remote_fname = "/etc/openvpn/static.key"
        
        fname_vpn_cfg = os.path.join(micro.config.cfg_dir, "openvpn.config")
        file_content = create_openvpn_client_cfg_file(micro.config.hostname)
        with open(fname_vpn_cfg, 'w') as f:
            f.write(file_content)
        
        fname_ros = os.path.join(micro.config.cfg_dir, "ros.sh")    
        file_content = create_ros_connect_file()
        with open(fname_ros, 'w') as f:
            f.write(file_content)
        
        fname_start_vpn = os.path.join(micro.config.cfg_dir, "start_vpn.sh")    
        file_content = create_vpn_connect_file()
        with open(fname_start_vpn, 'w') as f:
            f.write(file_content)
        
        vpnkey_fname = os.path.join(micro.config.cfg_dir, "openvpn.key")
        micro.scp_download_file(vpnkey_fname, remote_fname)
        
        fname_ssh_key =  os.path.join(micro.config.cfg_dir, micro.config.kp_name + '.pem')
        fname_ssh_sh =  os.path.join(micro.config.cfg_dir,'ssh.sh')
        fname_zip = os.path.join(micro.config.cfg_dir, "%s.zip" % micro.config.uid)
        
        print("creating %s" % fname_zip)
        with zipfile.ZipFile(fname_zip, 'w') as fzip:
            for fname in [fname_ssh_key, 
                          fname_ssh_sh, 
                          fname_vpn_cfg,
                          fname_ros,
                          vpnkey_fname]:
                short_fname = os.path.split(fname)[1]
                zip_name = os.path.join(micro.config.uid, short_fname)
                fzip.write(fname, zip_name)
        

    def test_micro_launch_vpn_2(self):
        root_directory = "test_launch_vpn"
        
        id = os.listdir(root_directory)[0]
        config_path = os.path.join(root_directory, id, "instance.json")
        print("machine %s" % config_path)
        self.assert_(os.path.exists(config_path), "no machine")
        
        
        publisher = StdoutPublisher("toto@toto.com")
        machine = Machine.from_file(config_path, publisher.event)
        
        repeats = 5
        for i in range(repeats):
            print("Checking status [%s / %s]" % (i+1, repeats))
            
            m = machine.test_aws_status()
            print("    aws status= %s" % m)
            p = machine.ping()
            print("    ping= %s" % str(p) )
            x = machine.test_X()
            print("    X= %s" % x)
            g = machine.test_gazebo()
            print("    gazebo= %s" % g)
            time.sleep(2)  
        print("Shuting down\n\n\n")      
        machine.terminate()
        print("\n\n\n")
        sys.stdout.flush()
        
        
class MachineDbTest(unittest.TestCase):
    
    def test_tags(self):
        
        set_machine_tag("a","b","c", "up", True, 10)
        x = get_machine_tag("a","b","c", "down")
        self.assert_(None == x, "")
        x = get_machine_tag("a","b","c", "up")
        self.assert_(True == x, "not found again")
         
    
    def atest_list_machines(self):
        dir = '/var/www-cloudsim-auth/machines'
        print('listing machines in "%s":' % dir)
        machines = list_all_machines_accross_domains(dir)
        for domain, constellation, machine in machines:
            print("   %s/%s/%s" % (domain, constellation['name'], machine.config.uid) )
            # print("done")
        
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main(testRunner = get_test_runner())        
 
