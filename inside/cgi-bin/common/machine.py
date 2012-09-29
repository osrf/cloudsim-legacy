import commands
import unittest

from . import *

class MachineException(Exception):
    pass

class Machine2 (object):
    
    def __init__(   self,
                    credentials_ec2 ,
                    pem_key_directory,
                    image_id,
                    instance_type,
                    security_groups,
                    username,
                    distro,):
        self.credentials_ec2 = credentials_ec2 # boto file
        self.pem_key_directory = pem_key_directory
        self.image_id = image_id
        self.instance_type = instance_type
        self.security_groups = security_groups
        self.username = username
        self.distro = distro
        self.ec2 = None
        self.hostname = None
        self.aws_id = None
        # This value is passed to ssh via -o ConnectTimeout=timeout
        self.ssh_connect_timeout = 1
        # We use this file as an indicator that our startup script has completed successfully
        self.startup_script_done_file = '/tmp/startup_script_done'
        self.ec2 = create_ec2_proxy(self.credentials_ec2)
        
        
    def launch(self, startup_script):
        
        self.startup_script = startup_script + '\ntouch %s\n'%(self.startup_script_done_file)
        
        print("create_team_login_instance")
        print("    BOTO file: %s" % self.credentials_ec2)
        print("    pem_key_directory: %s" % self.pem_key_directory)
        print("    image_id: %s" % self.image_id)
        print("    instance_type: %s" % self.instance_type)
        print("    security_groups: %s" % self.security_groups)
        print("    username: %s" % self.username)
        print("    distro: %s" % self.distro)
        

        self._create_machine_keys()
        
        try:
            # Start it up
            #print("Load startup script: image_id %s, security_group %s" % (image_id, security_group ) )
            res = self.ec2.run_instances(   image_id=self.image_id, 
                                            key_name=self.kp_name, 
                                            instance_type=self.instance_type, 
                                            security_groups = self.security_groups, 
                                            user_data=self.startup_script)
            
            print('    instance: %s' % res.id)
            print('    key file: %s' % self.kp_fname)
            
            # Wait for it to boot to get an IP address
            while True:
                done = False
                for r in self.ec2.get_all_instances():
                    if r.id == res.id and r.instances[0].public_dns_name:
                        done = True
                        break
                if done:
                    break
                else:
                    time.sleep(0.1)
        
            inst = r.instances[0]
            self.hostname = inst.public_dns_name
            self.aws_id = inst.id


        except Exception as e:
            # Clean up
            
            if os.path.exists(kp_fname):
                os.unlink(kp_fname)
                
            cfg_dir=os.path.join(pem_key_directory, uid)
            os.rmdir(cfg_dir)
            # re-raise
            raise

    def _create_machine_keys(self):
        
        #ec2, pem_key_directory, image_id, instance_type, username, distro
    
        self.uid = str(uuid.uuid1())
        
        cfg_dir=os.path.join(self.pem_key_directory, self.uid)
        if os.path.exists(cfg_dir):
            print('Directory/file %s already exists; bailing'%(cfg_dir))
            raise MachineException('UUID creation did not meet expectations')
       

        # save the ssh key
        self.kp_name = 'key-%s'%(self.uid)
        kp = self.ec2.create_key_pair(self.kp_name)
        os.makedirs(cfg_dir)
        kp.save(cfg_dir)
        self.kp_fname = os.path.join(cfg_dir, self.kp_name + '.pem')


    def ssh_send_command(self, cmd, extra_ssh_args=[]):
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', self.kp_fname] + extra_ssh_args + ['%s@%s'%(self.username, self.hostname)]
        ssh_cmd.extend(cmd)
        po = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode != 0:
            raise MachineException(out + err)
        else:
            return out

    def scp_send_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(self.ssh_connect_timeout), '-i', self.kp_fname] + extra_scp_args + [local_fname, '%s@%s:%s'%(self.username, self.hostname, remote_fname)]
        scp_cmd_string = ' '.join(scp_cmd)
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise MachineException('scp failed: %s'%(output))
        else:
            return output

    def user_ssh_command(self):
        return "ssh -i %s %s@%s"%(self.kp_fname, self.username, self.hostname)

    def ssh_wait_for_ready(self, retries=200, delay=0.1, file_to_look_for=None):
        if not file_to_look_for:
            file_to_look_for = self.startup_script_done_file
        cmd = ['ls', file_to_look_for]
        tries = 0
        sys.stdout.write("%s retries " % retries)
        while tries < retries:
            tries += 1
            # print ( "%s / %s" % (tries, retries))
            sys.stdout.write('.')
            sys.stdout.flush()
            try:
                self.ssh_send_command(cmd)
            except MachineException as ex:
                # Expected; e.g., the machine isn't up yet
                time.sleep(delay)
            else:
                print ("    Success")
                return
        raise MachineException("Maximum retry limit exceeded; ssh connection could not be established.")
    
    def terminate(self):
        terminated_list = self.ec2.terminate_instances(instance_ids=[self.aws_id])
        if(len(terminated_list) == 0 ):
            raise MachineException("Could not terminate instance %s" % self.aws_id)
        print("terminated " % terminated_list[0])
        
    
#########################################################################
    
class MachineCase(unittest.TestCase):

    def test_start_stop(self):

        try:
            micro = Machine2(credentials_ec2 = '../../../../boto.ini', 
                         pem_key_directory = 'test_pems', 
                         image_id ='', 
                         instance_type = 't1.micro' , 
                         security_groups = ['ping_ssh'], 
                         username = 'ubuntu', 
                         distro = 'precise')
            
            startup_script = "#!/bin/bash\necho hello > test.txt\n\n"
            
            micro.launch(startup_script)
    
            print("Machine launched at: %s"%(team_login.hostname))
            print("\nIn case of emergency:\n\n%s\n\n"%(team_login.user_ssh_command()))
            print("Waiting for ssh")
            team_login.ssh_wait_for_ready()
            print("Good to go.")
            
            print("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )
            team_login.scp_send_file(website_distribution, remote_fname)
            
            #checking that the file is there
            short_file_name = os.path.split(website_distribution)[1] 
            remote_fname = "/home/%s/test.txt" % (team_login.username)
            team_login.ssh_send_command(["ls", remote_fname ] )
            
            # terminate machine
            micro.terminate()
            
        finally:
            commands.getoutput('rm -rf test_pems')
        
         
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()        
 