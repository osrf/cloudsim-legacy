import commands
import unittest

import uuid
import boto
import os
import sys
import time
import subprocess
import  common 
import json




class MachineException(Exception):
    pass

def create_ec2_proxy(boto_config_file):
    # Load boto config from indicated file.  By overwriting boto.config,
    # our new config will be used.
    boto.config = boto.pyami.config.Config(boto_config_file)

    # No args: uses config from boto.config
    ec2 = boto.connect_ec2()
    return ec2


class Machine_configuration(object):

    @classmethod
    def from_file(cls, fname):
        with open(fname,'r') as fp:
            dict = json.load(fp)
            #x = Machine_configuration(**dict)
            x = Machine_configuration()
            x.__dict__.update(dict)
            fp.close()
            return x
    
    def __init__(self):
        pass
        
    def initialize(self, 
                 pem_key_directory,
                 credentials_ec2 ,   
                 image_id,
                 instance_type,
                 security_groups,
                 username,
                 distro):

        # launching parameters
        self.credentials_ec2 = credentials_ec2 # boto file
        self.pem_key_directory = pem_key_directory
        self.image_id = image_id
        self.instance_type = instance_type
        self.security_groups = security_groups
        self.username = username
        self.distro = distro
    
    def save_json(self, fname):
        print("save json:",self.__dict__) 
        with open(fname,'w') as fp:
            json.dump(self.__dict__, fp) #, skipkeys, ensure_ascii, check_circular, allow_nan, cls, indent, separators, encoding, default)
            fp.close()

    def print_cfg(self):
        print("Machine configuration")
        for item in self.__dict__:
            print ("%s: %s" % (item, self.__dict__[item]) )
                       
    

class Machine2 (object):
    
    def __init__(   self,
                    config, 
                    startup_script, do_launch = True):
        self.config = config
        self.ssh_connect_timeout = 1
        # We use this file as an indicator that our startup script has completed successfully
        self.startup_script_done_file = '/tmp/startup_script_done'
        self.ec2 = create_ec2_proxy(self.config.credentials_ec2)
        if do_launch:
            self._launch(startup_script)
            fname = os.path.join(self.config.cfg_dir, 'config.json')
            self.config.save_json(fname)

    @classmethod
    def from_file(cls,  fname):
        config = Machine_configuration.from_file(fname)
        script = config.startup_script
        x = Machine2(config, script, do_launch = False)  
        return x
                
    def _event(self, event_name, event_data=None):
        data = event_data
        print("event: %s" % (event_name)) 
        if event_data:
            print("data:%s" %  (event_data))
        print("")
        sys.stdout.flush()
        
                        
    def _launch(self, startup_script):
        
        self.config.startup_script = startup_script + '\ntouch %s\n'%(self.startup_script_done_file)
        self._create_machine_keys()
        try:
            # Start it up
            self._event("action", "{state:run}")
            res = self.ec2.run_instances(   image_id=self.config.image_id, 
                                            key_name=self.config.kp_name, 
                                            instance_type=self.config.instance_type, 
                                            security_groups = self.config.security_groups, 
                                            user_data=self.config.startup_script)
           
            #self.config.print_cfg()
            
            self.config.reservation = res.id
            self._event("milestone", "{state:reserved, reservation_id:'%s'}" % self.config.reservation)
            self._event("action", "{state:'waiting_for_ip'}") # print('Wait for it to boot to get an IP address')
            
            # to do: add retries
            while True:
                self._event("action", "{state:'waiting_for_ip'}") # print('Wait for it to boot to get an IP address')
                done = False
                for r in self.ec2.get_all_instances():
                    if r.id == res.id and r.instances[0].public_dns_name:
                        done = True
                        self._event("milestone", "{state:'ip_set'}")
                        break
                if done:
                    break
                else:
                    time.sleep(0.1)
        
            inst = r.instances[0]
            self.config.hostname = inst.public_dns_name
            self.config.aws_id = inst.id
            
        except Exception as e:
            # Clean up
            
            if os.path.exists(self.config.kp_fname):
                os.unlink(self.config.kp_fname)
                
            #cfg_dir=os.path.join(pem_key_directory, uid)
            os.rmdir(self.config.cfg_dir)
            # re-raise
            raise

    def _create_machine_keys(self):
        
        #ec2, pem_key_directory, image_id, instance_type, username, distro
        self.config.uid = str(uuid.uuid1())
        self.config.cfg_dir=os.path.join(self.config.pem_key_directory, self.config.uid)
        
        if os.path.exists(self.config.cfg_dir):
            print('Directory/file %s already exists; bailing'%(self.config.cfg_dir))
            raise MachineException('UUID creation did not meet expectations')
       
        # save the ssh key
        self.config.kp_name = 'key-%s'%(self.config.uid)
        kp = self.ec2.create_key_pair(self.config.kp_name)
        os.makedirs(self.config.cfg_dir)
        kp.save(self.config.cfg_dir)
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

    def user_ssh_command(self):
        return "ssh -i %s %s@%s"%(self.config.kp_fname, self.config.username, self.config.hostname)

    def ssh_wait_for_ready(self, retries=200, delay=0.1, file_to_look_for=None):
        if not file_to_look_for:
            file_to_look_for = self.startup_script_done_file
        cmd = ['ls', file_to_look_for]
        tries = 0
        self._event("action", "{state:'ssh_wait_for_ready', try:%s, retries:%s}" % (tries, retries) )
        sys.stdout.write("%s retries " % retries)
        
        while tries < retries:
            tries += 1
            # print ( "%s / %s" % (tries, retries))
            self._event("action", "{state:'ssh_wait_for_ready', try:%s, retries:%s}" % (tries, retries) )
            sys.stdout.flush()
            try:
                self.ssh_send_command(cmd)
            except MachineException as ex:
                # Expected; e.g., the machine isn't up yet
                time.sleep(delay)
            else:
                self._event("milestone", "{state:'ssh_connected'}")
                return
        raise MachineException("Maximum retry limit exceeded; ssh connection could not be established or file '%s' not found" % file_to_look_for)
    
    def terminate(self):
        terminated_list = self.ec2.terminate_instances(instance_ids=[self.config.aws_id])
        if(len(terminated_list) == 0 ):
            raise MachineException("Could not terminate instance %s" % self.config.aws_id)
        print("{state:'terminated', machine_id:'%s'" % terminated_list[0])
        
        
    
#########################################################################
    
class MachineCase(unittest.TestCase):
    
    def test_config(self):
        
        config = Machine_configuration()
        config.initialize(pem_key_directory = 'test_pems', 
                                         credentials_ec2 = '../../../../boto.ini', 
                                         image_id ="ami-137bcf7a", 
                                         instance_type = 't1.micro' , 
                                         security_groups = ['ping_ssh'], 
                                         username = 'ubuntu', 
                                         distro = 'precise')
        fname = "test_machine.config"
        config.save_json(fname)
        
        config2 = Machine_configuration.from_file(fname)
        print("\nfrom file:")
        config2.print_cfg()
        self.assertEqual(config.image_id, config2.image_id, "json fail")
        

    def test_start_stop(self):

        try:
            
            config = Machine_configuration()
            
            config.initialize(   pem_key_directory = 'test_pems', 
                                 credentials_ec2 = '../../../../boto.ini', 
                                 image_id ="ami-137bcf7a", 
                                 instance_type = 't1.micro' , 
                                 security_groups = ['ping_ssh'], 
                                 username = 'ubuntu', 
                                 distro = 'precise')
                   
            startup_script = "#!/bin/bash\necho hello > test.txt\n\n"
            micro_original  = Machine2(config, startup_script)

            fname = 'test_pems/machine.instance'
            print('saving machine instance info to "%s"'%fname)
            micro_original.config.save_json(fname)
           
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

            micro.terminate()
            
        finally:
            commands.getoutput('rm -rf test_pems')
        
         
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()        
 
