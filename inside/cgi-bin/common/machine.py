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
import common
 
import boto

from machine_configuration import Machine_configuration
from chardet import constants

from constants import *
from startup_script_builder import *
import zipfile

"""
Removes the key for this ip, in case we connect to a different machine with the
same key in the future. This avoids ssh messages
"""
def clean_local_ssh_key_entry( hostname):
    cmd = 'sudo ssh-keygen -f "/var/www/.ssh/known_hosts" -R %s' % hostname
    s,o = commands.getstatusoutput(cmd)
    
    print("clean_local_ssh_key_entry for %s" % hostname)
    print(o)
    print
    return s

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
        
       
        
class Machine2 (object):
    
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
            self.config.uid = unique_name
            self.config.root_directory = root_directory
            self.config.cfg_dir=os.path.join(self.config.root_directory, self.config.uid)
            os.makedirs(self.config.cfg_dir)
            
            self.config.launch_log_fname = os.path.join(self.config.cfg_dir, 'launch.log')
            self.log = open(self.config.launch_log_fname, 'w')
            self.config.instance_fname = os.path.join(self.config.cfg_dir, 'instance.json')
            
            self.config.save_json(self.config.instance_fname)
            self._create_machine_keys() 
            self.config.save_json(self.config.instance_fname)
            
            self._launch()
            
            self.config.save_json(self.config.instance_fname)
            self.log.close()
            self.log = None
        else:
            self.ec2 = create_ec2_proxy(self.config.credentials_ec2 )

    @classmethod
    def from_file(cls,  fname, event = None):
        if(event == None):
            x = StdoutPublisher()
            event = x.event
        config = Machine_configuration.from_file(fname)
        x = Machine2(config.uid, config, event, do_launch = False)
        return x

    def _event(self, data_dict):
        if self.event:
            data_dict['machine'] = self.config.uid
            self.event(data_dict)
        
    def _evento(self, event_name, event_data=None):
        
        if self.log:    
            event_str = "event: %s" % (event_name)
            self.log.write("%s\n" % event_str)
            if event_data:
                data_str = "data:%s\n" %  (event_data)
            self.log.write("%s\n\n" % data_str)
            self.log.flush()
        
        if self.event:
            self.event(event_name, event_data)    
        
            

    def _launch(self):
        
        self.config.startup_script += '\ntouch %s\n'%(self.startup_script_done_file)
        try:
            # Start it up
            
            self._event({"type:":"action", "state":"reserve"})
            res = self.ec2.run_instances(   image_id=self.config.image_id, 
                                            min_count =1,
                                            max_count =1,
                                            key_name=self.config.kp_name, 
                                            instance_type=self.config.instance_type, 
                                            security_groups = self.config.security_groups, 
                                            user_data=self.config.startup_script)
            #self.config.print_cfg()
            self.config.reservation = res.id
            self._event({"type":"check", "state":"reserve", "reservation_id":'%s'% self.config.reservation } )
            
            self._event({"type": "action", "state":"waiting_for_ip"})
            retries = self.config.ip_retries
            tries = 0
            while tries< retries:
                done = False
                tries += 1
                self._event({"type":"retry", "state":'ip_set', "try":tries, "retries":retries} )
                for r in self.ec2.get_all_instances():
                    if r.id == res.id and r.instances[0].public_dns_name:
                        done = True
                        inst = r.instances[0]
                        self.config.hostname = inst.public_dns_name
                        self.config.ip = inst.ip_address
                        self.config.aws_id = inst.id
                        self._event({"type":"check", "state":'ip_set', "ip": self.config.ip })
                        break
                    time.sleep(0.1)
                if done:
                    break 
                
            if tries >= retries:
                self._event({"type":"fail", "state":'ip_set'})
                raise MachineException("Can't get IP for machine reservation '%s'" % self.config.reservation)
            if len(self.config.tags):
                self._event({"type": "action", "state":'tags_set'})
                self.ec2.create_tags([self.config.aws_id], self.config.tags)
                self._event({"type":"check", "state":'tags_set'})
            
            
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

    def user_ssh_command(self):
        return "ssh -i %s %s@%s"%(self.config.kp_fname, self.config.username, self.config.hostname)

    def ssh_wait_for_ready(self, the_file_to_look_for=None):
        delay = 0.5
        file_to_look_for = the_file_to_look_for
        if not file_to_look_for:
            file_to_look_for = self.startup_script_done_file
        cmd = 'ls %s' %  file_to_look_for
        
        retries = self.config.ssh_retries
        tries = 0
        self._event({"type" :"action", "state":'ssh_wait_for_ready', "file":file_to_look_for, "try": tries, "retries":retries })
        while tries < retries:
            tries += 1
            # print ( "%s / %s" % (tries, retries))
            self._event({"type":"retry", "state":'ssh_wait_for_ready', "file": file_to_look_for,  "try": tries, "retries": retries })
            sys.stdout.flush()
            try:
                self.ssh_send_command(cmd)
            except MachineException as ex:
                # Expected; e.g., the machine isn't up yet
                time.sleep(delay)
            else:
                self._event({"type" : "check", "state":'ssh_connected'})
                return
        self._event({"type":"fail", "state":'ssh_connected'})   
        raise MachineException("Maximum retry limit exceeded; ssh connection could not be established or file '%s' not found" % file_to_look_for)
    
    def terminate(self):
        self._event({"type":"action", "state":'terminated'})
        terminated_list = self.ec2.terminate_instances(instance_ids=[self.config.aws_id])
        if(len(terminated_list) == 0 ):
            self._event({"type":"fail", "state":'terminated', 'machine_id': self.config.aws_id})
            raise MachineException("Could not terminate instance %s" % self.config.aws_id)
        self.ec2.delete_key_pair(self.config.kp_name)
        self._event({"type":"check", "state":'terminated', "machine_id":self.config.aws_id})
    
    def test_X(self):
        self._event({"type":"test", "state":'X, OpenGL'})
        try:
            r = self.ssh_send_command('DISPLAY=localhost:0; glxinfo')
            self._event({"type":"check", "state":'X, OpenGL'})
            return True
        except:
            self._event({"type":"fail", "state":'X, OpenGL'})
            return False

    def ping(self, count = 3):
        self._event({"type":"test", "state":'latency', 'count':count})
        host = self.config.hostname
        try:
            min, avg, max, mdev = ping(host, count)
            self._event({"type":"check", "state":'latency', 'count':count, 'min':min, 'avg':avg, 'max':max, 'mdev':mdev})
            return True
        except:
            self._event({"type":"fail", "state":'latency'})
        return False

    def test_gazebo(self):
        self._event({"type":"test", "state":'simulation'})
        d = self.config.distro
        cmd = 'source /opt/ros/%s/setup.bash && rosrun gazebo gztopic list' % d 
        try:
            r = self.ssh_send_command(cmd)
            self._event({"type":"check", "state":'simulation'}) 
            return True
        except:
            self._event({"type":"fail", "state":'simulation'})
            return False

    def test_aws_status(self, timeout=1):
        self._event({"type":"test", "state":'aws'})
        try:
            
            for r in self.ec2.get_all_instances():
                for i in r.instances:
                    if i.id == self.config.aws_id:
                        self._event({"type":"check", "state":'cloud', 'status':i.state}) 
                        return True 
            self._event({"type":"fail", 'state':'cloud', 'status':"Unable to find machine at AWS"})
            return False
        except Exception as e:
            self._event({"type":"fail", 'state':'cloud', 'status':str(e)})
            return False

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

class MachineDb(object):
    
    def __init__(self, email, machine_dir = MACHINES_DIR):
        self.user = email
        self.domain = email.split('@')[1]
        self.root_dir =  os.path.join(machine_dir, self.domain)
        
        
    def get_machines(self):
        machines = {}
        for short_name in os.listdir(self.root_dir):
            machine = self.get_machine(short_name)
            machines[short_name] = machine 
        return machines
    
    def get_machine(self, name):
        fname =  os.path.join(self.root_dir, name, 'instance.json')
        machine = Machine2.from_file(fname)
        return machine
    
    def get_machines_as_json(self):
        machines = self.get_machines()
        l = []
        l.append("{")
        
        for name, machine in machines.iteritems():
            l.append( '"%s":' % name)
            # str += machine.config.as_json()
            l.append('{name:"hi"}')
            l.append(",")
        l.append("}")
        str = "".join(l)
        return str   

    def get_launch_log_fname(self, machine_name):
        fname =  os.path.join(self.root_dir, machine_name, "launch.log")
        return fname

#########################################################################


INSTALL_VPN = """

echo "Installing openvpn" >> /home/ubuntu/setup.log

# Install and start openvpn.  Do this last, because we're going to 
# infer that the machine is ready from the presence of the 
# openvpn static key file.
apt-get install -y openvpn

echo "Generating openvpn key" >> /home/ubuntu/setup.log
openvpn --genkey --secret static.key

echo "Setting key permissions" >> /home/ubuntu/setup.log
chmod 644 static.key

echo "Set up for autostart by copying conf to /etc/openvpn" >> /home/ubuntu/setup.log 
cp openvpn.config /etc/openvpn/openvpn.conf
cp static.key /etc/openvpn/static.key

echo "Start openvpn" >> /home/ubuntu/setup.log
service openvpn start

echo "Setup complete" >> /home/ubuntu/setup.log

"""

class PingTest(unittest.TestCase):
    
    def test_a_ping(self):
        
        print( "ping google.com 3x: (min, avg, max, mdev)")
        min, avg, max, mdev  = ping("google.com", 3)
        print ("min, avg, max, mdev\n", min, avg, max, mdev)
        self.assert_(max > min, "bad pong")
        self.assert_(min > 1.0, "bad pong")
        
        caught = False
        try:
            r = ping("xYZ_google_XYZ.com", 3)
        except MachineException, e:
            caught = True
            print(e)
        
        self.assert_(caught)
        
             
class MachineCase(unittest.TestCase): 

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

        micro = Machine2(machine_name,
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
        machine = Machine2.from_file(config_path, publisher.event)
        
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
        
    
           
         
        
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()        
 
