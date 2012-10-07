from __future__ import print_function
import os
import tempfile
import subprocess
import Cookie
import boto
import cgi
import stat
import cgitb
import unittest

from constants import *
# TODO: turn this back on 
# cgitb.enable()


DISABLE_AUTHENTICATION_FOR_DEBUG_PURPOSES_ONLY = False





def get_user_database():
    # Load user database
#    users = []
#    with open(USER_DATABASE, 'r') as f:
#        for u in f.readlines():
#            users.append(u.strip())
#    return users
    db = UserDatabase()
    return db.get_users()

class CloudCredentials(object):
    
    def __init__(self, 
                 aws_access_key_id, 
                 aws_secret_access_key, 
                 ec2_region_name = 'us-east-1', 
                 ec2_region_endpoint = 'ec2.amazonaws.com', 
                 fname = BOTO_CONFIG_FILE_USEAST ):
        
        self.fname = fname
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
                
        self.config_text = """
[Credentials]
aws_access_key_id = %s
aws_secret_access_key = %s

[Boto]
ec2_region_name = %s
ec2_region_endpoint = %s
"""    % (aws_access_key_id, self.aws_secret_access_key, ec2_region_name, ec2_region_endpoint)
        
        
    
    def save(self ):
        with open(self.fname, 'w') as f:
            f.write(self.config_text)
            f.close()

    def validate(self):
        from boto.ec2.connection import EC2Connection
        try:
            conn = EC2Connection(self.aws_access_key_id, self.aws_secret_access_key)
            conn.get_all_zones()
        except:
            return False
        return True
        






class Machine:
    def __init__(self, name, path, incomplete_ok=False):
        self.name = name
        self.path = path
        try:
            self.openvpn_config_fname = os.path.join(self.path, OPENVPN_CONFIG_FNAME)
            self.openvpn_config = open(self.openvpn_config_fname).read()
            self.openvpn_key_fname = os.path.join(self.path, 'openvpn-%s.key'%(self.name))
            self.openvpn_key = open(self.openvpn_key_fname).read()
            self.ssh_key_fname = os.path.join(self.path, 'key-%s.pem'%(self.name))
            self.ssh_key = open(self.ssh_key_fname).read()
            self.hostname_fname = os.path.join(self.path, HOSTNAME_FNAME)
            self.hostname = open(self.hostname_fname).read().strip()
            self.username_fname = os.path.join(self.path, USERNAME_FNAME)
            self.username = open(self.username_fname).read().strip()
            self.aws_id_fname = os.path.join(self.path, AWS_ID_FNAME)
            self.aws_id = open(self.aws_id_fname).read().strip()
            self.botofile_fname = os.path.join(self.path, BOTOFILE_FNAME)
            self.botofile = open(self.botofile_fname).read().strip()
            self.ros_sh_fname = os.path.join(self.path, ROS_SH_FNAME) 
            self.ros_sh = open(self.ros_sh_fname).read().strip()
            
            self.incomplete = False
        except Exception as e:
            if incomplete_ok:
                self.incomplete = True
            else:
                raise

    def ping(self, timeout=1.0):
        cmd = ['ping', '-c', '1', '-w', '%f'%(timeout), self.hostname]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        # ping returns 0 when it's happy
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def test_ssh(self, timeout=1, fname='/%s'%(OPENVPN_STATIC_KEY_FNAME)):
        return self.ssh(['ls', fname], timeout=timeout)

    def test_X(self, timeout=1):
        return self.ssh(['DISPLAY=localhost:0', 'glxinfo'], timeout=timeout)

    def test_gazebo(self, timeout=1):
        return self.ssh(['source /opt/ros/%s/setup.bash && rosrun gazebo gztopic list'%(DISTRO)], timeout=timeout)

    def ssh(self, cmd, timeout=1, args=[]):
        ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname] + args + ['%s@%s'%(self.username, self.hostname)]
        ssh_cmd.extend(cmd)
        po = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def get_aws_status(self, timeout=1):
        try:
            ec2 = create_ec2_proxy(self.botofile)
            for r in ec2.get_all_instances():
                for i in r.instances:
                    if i.id == self.aws_id:
                           return (True, i.state)
            return (False, "Unable to find machine at AWS")
        except Exception as e:
            return (False, str(e))

    def reboot(self, timeout=1):
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'sudo', 'reboot']
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def terminate(self, timeout=1):
        try:
            ec2 = create_ec2_proxy(self.botofile)
            ec2.terminate_instances([self.aws_id])
        except Exception as e:
            return False, str(e)
        return True, ''

    def stop(self, timeout=1):
        ec2 = create_ec2_proxy(self.botofile)
        try:
            ec2.stop_instances([self.aws_id])
        except Exception as e:
            return False, str(e)
        return True, ''

    def start(self, timeout=1):
        ec2 = create_ec2_proxy(self.botofile)
        try:
            ec2.start_instances([self.aws_id])
        except Exception as e:
            return False, str(e)
        return True, ''

def create_ec2_proxy(boto_config_file):
    # Load boto config from indicated file.  By overwriting boto.config,
    # our new config will be used.
    boto.config = boto.pyami.config.Config(boto_config_file)

    # No args: uses config from boto.config
    ec2 = boto.connect_ec2()
    return ec2
        
def list_machines(email):
    domain = email.split('@')[1]
    userdir = os.path.join(MACHINES_DIR, domain)
    machines = []
    incompletes = []
    if os.path.isdir(userdir):
        for f in os.listdir(userdir):
            try:
                machines.append(Machine(f, os.path.join(userdir,f)))
            except Exception as e:
                # Separate corrupt machine directories
                incompletes.append(Machine(f, os.path.join(userdir,f), incomplete_ok=True))
    return (machines,incompletes)

# Launch a long-running background process.  script can be anything 
# that bash will understand
def start_background_task(script):
    with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
        tmpfile.write(script)
    os.chmod(tmpfile.name, stat.S_IRUSR | stat.S_IXUSR | stat.S_IWUSR | stat.S_IROTH | stat.S_IXOTH | stat.S_IRGRP | stat.S_IXGRP)
    # Note: www-data user must not be in the /etc/at.deny file
    cmd = ['bash', '-c', 'at NOW <<< %s'%(tmpfile.name)]
    po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = po.communicate()
    #os.unlink(tmpfile.name)
    if po.returncode != 0:
        raise Exception('start_background_task() failed: %s; %s'%(out, err))

#########################################################################
    
class AdminDb(unittest.TestCase):

    def test_addremove_users(self):
        db = UserDatabase('toto.txt')
        users = db.get_users()
        self.assert_(len(users) == 0, "not empty!")
        db.add_user('toto@popo.com')
        self.assert_(len(db.get_users()) == 1, "not added!")
        db.remove_user('not_a_real_user@popo.com')
        self.assert_(len(db.get_users()) == 1, "not not removed!")
        db.remove_user('toto@popo.com')
        self.assert_(len(db.get_users()) == 0, "not removed!")
    
    def test_credentials(self):
        cloud = CloudCredentials('aws_access_key_id', 'aws_secret_access_key', 'ec2_region_name', 'ec2_region_endpoint', 'toto.cfg' )
        valid = cloud.validate()
        self.assert_(valid == False, "valid?")
        cloud.save()
        self.assert_(os.path.exists('toto.cfg'), 'no cred!')
         
        
if __name__ == '__main__':
    print('COMMON TESTS')
    unittest.main()    

