from __future__ import with_statement
from __future__ import print_function

import commands
import unittest
import uuid
import boto
import os
import sys
import time
import subprocess
import json
import shutil
import common 


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


class MachineException(Exception):
    pass

def create_ec2_proxy(boto_config_file):
    boto.config = boto.pyami.config.Config(boto_config_file)
    ec2 = boto.connect_ec2()
    return ec2


class Machine2 (object):
    
    def __init__(   self,
                    config, 
                    tags ={},
                    credentials_ec2 = BOTO_CONFIG_FILE_USEAST, # boto file
                    root_directory = MACHINES_DIR,
                    do_launch = True):
        
        self.log = None
        self.config = config
        self.startup_script_done_file = '/tmp/startup_script_done'
        self.ssh_connect_timeout = 1
        
        # We use this file as an indicator that our startup script has completed successfully
        self.ec2 = create_ec2_proxy(credentials_ec2)
        
        if do_launch:
            self.config.tags = tags
            self.config.uid = str(uuid.uuid1())
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

    @classmethod
    def from_file(cls,  fname):
        config = Machine_configuration.from_file(fname)
        x = Machine2(config, do_launch = False)  
        
        return x
                
    def _event(self, event_name, event_data=None):
        data = event_data
        event_str = "event: %s" % (event_name)
        print(event_str)
        if self.log:    
            self.log.write("%s\n" % event_str)
            
        if event_data:
            data_str = "data:%s\n" %  (event_data)
            print(data_str)
            if self.log:
                self.log.write("%s\n\n" % data_str)
        sys.stdout.flush()
        if self.log:
            self.log.flush()
                        
    def _launch(self):
        
        self.config.startup_script += '\ntouch %s\n'%(self.startup_script_done_file)
        try:
            # Start it up
            self._event("action", "{state:'reserve'}")
            res = self.ec2.run_instances(   image_id=self.config.image_id, 
                                            min_count =1,
                                            max_count =1,
                                            key_name=self.config.kp_name, 
                                            instance_type=self.config.instance_type, 
                                            security_groups = self.config.security_groups, 
                                            user_data=self.config.startup_script)
           
            #self.config.print_cfg()
            
            self.config.reservation = res.id
            self._event("check", "{state:reserve, reservation_id:'%s'}" % self.config.reservation)
                        
            self._event("action", "{state:'waiting_for_ip'}")
            retries = self.config.ip_retries
            tries = 0
            while tries< retries:
                done = False
                tries += 1
                self._event("retry", "{state:'ip_set', try:%s, retries:%s}" % (tries, retries) )
                for r in self.ec2.get_all_instances():
                    if r.id == res.id and r.instances[0].public_dns_name:
                        done = True
                        inst = r.instances[0]
                        self.config.hostname = inst.public_dns_name
                        self.config.ip = inst.ip_address
                        self.config.aws_id = inst.id
                        self._event("check", "{state:'ip_set', ip:'%s'}" % self.config.ip)
                        break
                    time.sleep(0.1)
                if done:
                    break 
                
            if tries >= retries:
                self._event("fail", "{state:'ip_set'}")
                raise MachineException("Can't get IP for machine reservation '%s'" % self.config.reservation)
    
            
            
            if len(self.config.tags):
                self._event("action", "{state:'tags_set'}")
                self.ec2.create_tags([self.config.aws_id], self.config.tags)
                self._event("check", "{state:'tags_set'}")
            
            
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
        ssh_cmd.extend(cmd)
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
        cmd = ['ls', file_to_look_for]
        
        retries = self.config.ssh_retries
        tries = 0
        self._event("action", "{state:'ssh_wait_for_ready', try:%s, retries:%s}" % (tries, retries)) 
        while tries < retries:
            tries += 1
            # print ( "%s / %s" % (tries, retries))
            self._event("retry", "{state:'ssh_wait_for_ready', try:%s, retries:%s}" % (tries, retries) )
            sys.stdout.flush()
            try:
                self.ssh_send_command(cmd)
            except MachineException as ex:
                # Expected; e.g., the machine isn't up yet
                time.sleep(delay)
            else:
                self._event("check", "{state:'ssh_connected'}")
                return
        self._event("fail", "{state:'ssh_connected'}")   
        raise MachineException("Maximum retry limit exceeded; ssh connection could not be established or file '%s' not found" % file_to_look_for)
    
    def terminate(self):
        self._event("action", "{state:'terminated'}")
        terminated_list = self.ec2.terminate_instances(instance_ids=[self.config.aws_id])
        if(len(terminated_list) == 0 ):
            self._event("fail", "{state:'terminated, machine_id:'%s'}" % terminated_list[0])   
            raise MachineException("Could not terminate instance %s" % self.config.aws_id)
        self._event("check", "{state:'terminated, machine_id:'%s'}" % terminated_list[0]) 
        

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
        fname =  os.path.join(self.root_dir, name)
        
        #machine = Machine2.from_file(fname)
        
        # print(fname," file <br>")
        machine = {'toto':'toto'}
        
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


     
class MachineCase(unittest.TestCase): 
    
    def test_launch_vpn(self):
        
        root_directory = "test_launch_vpn"
        
        
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
                
        micro = Machine2(config, tags,
                                   credentials_ec2 = "/home/hugo/code/boto.ini", # boto file
                                   root_directory = root_directory)
        
        micro.create_ssh_connect_script()
        clean_local_ssh_key_entry(micro.config.ip )
        
        micro.ssh_wait_for_ready()
        
        
        remote_fname = "/etc/openvpn/static.key"
        
        
#        fname = os.path.join(zip_dir_name, "ssh.sh")
#        with open(fname, 'w') as f:
#            s = create_ssh_connect_file(micro.config.kp_name + '.pem', micro.config.ip, micro.config.username)
#            f.write(s)
        
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
        print ("Downloading key file %s" % vpnkey_fname)
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
        

    """
    This test is longer: it creates a machine instance, and kills it
    """
    def atest_start_stop(self):

        try:
            
            startup_script = "#!/bin/bash\necho hello > test.txt\n\n"
            
            config = Machine_configuration()
            config.initialize(   image_id ="ami-137bcf7a", 
                                 instance_type = 't1.micro' , 
                                 security_groups = ['ping_ssh'],
                                 username = 'ubuntu', 
                                 distro = 'precise',
                                 startup_script = startup_script,
                                 ip_retries=100, 
                                 ssh_retries=200)
            
            
            tags = {'hello':'world', 'user':'toto@toto.com'}
            
            
            micro_original  = Machine2(config, tags,
                                       credentials_ec2 = "/home/hugo/code/boto.ini", # boto file
                                       root_directory = "test_machines",)
            
            clean_local_ssh_key_entry(micro_original.config.ip )
            
            fname = 'test_machines/machine_case.instance'
            print('saving machine instance info to "%s"'%fname)
            micro_original.config.save_json(fname)
            
            fname = micro_original.config.instance_fname

            #
            # !!!
            # From now on we're using a new Machine instance, initialized by the json data
            #  
            #
            
            micro = Machine2.from_file(fname)
            print("Machine launched at: %s"%(micro.config.hostname))
            print("\nIn case of emergency:\n\n%s\n\n"%(micro.user_ssh_command()))
            print("Waiting for ssh")
            micro.ssh_wait_for_ready()
            print("Good to go.")            
            print ("tags original: %s, new: %s" % (micro_original.config.tags, micro.config.tags))
            # check tag (this is not from the ec2... only from local state
            

            micro.terminate()
            self.assertEqual(micro.config.tags['hello'] , 'world', 'Not tagged')
            
        finally:
           commands.getoutput('rm -rf test_pems')
           
         
        
        
        
        
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()        
 
