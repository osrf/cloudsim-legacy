import logging
import commands
import os
import subprocess

def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launch", msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)

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


#def wait_for_ssh(self, public_ip, key_file, fname='/done', username = 'ubuntu'):
#    ssh_cmd = ['ssh', '-o', 'StrictHostKeyChecking=no',
#           '-i', '%s.pem'%(key_file), '%s@%s'%(username,
#           public_ip), 'ls %s' % fname]
#    while True:
#        po = subprocess.Popen(ssh_cmd)
#        po.communicate()
#        if po.returncode == 0:
#            break