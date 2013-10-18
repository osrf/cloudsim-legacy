import commands
import os
import subprocess
from launch_db import log_msg


def log(msg, channel=__name__, severity="debug"):
    log_msg(msg, channel, severity)


def clean_local_ssh_key_entry(hostname):
    """
    Removes the key for this ip, in case we connect to a different machine with
    the same key in the future. This avoids ssh warning messages
    """
    www_ssh_host_file = "/var/www/.ssh/known_hosts"
    if os.path.exists(www_ssh_host_file):
        cmd = 'ssh-keygen -f %s -R %s' % (www_ssh_host_file, hostname)
        s, o = commands.getstatusoutput(cmd)
        print("clean_local_ssh_key_entry for %s" % hostname)
        print(o)
        print
        return s
    else:
        return ""


class SshClientException(Exception):
    pass


class SshClient(object):
    def __init__(self, constellation_directory, key_name, username, ip):

        clean_local_ssh_key_entry(ip)

        self.key_fname = os.path.join(constellation_directory,
                                      "%s.pem" % key_name)
        self.user = '%s@%s' % (username, ip)
        self.ssh_connect_timeout = 10
        self.ip = ip

    def cmd(self, cmd, extra_ssh_args=[]):
        ssh_cmd = ['ssh',
                   '-o', 'UserKnownHostsFile=/dev/null',
                   '-o', 'StrictHostKeyChecking=no',
                   '-o', 'ConnectTimeout=%d' % (self.ssh_connect_timeout),
                   '-i', self.key_fname] + extra_ssh_args + [self.user]

        ssh_cmd.append(cmd)
        log(" ".join(ssh_cmd))
        po = subprocess.Popen(ssh_cmd,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out, err = po.communicate()
        #log("    CMD out: %s" % out)
        #log("    CMD err: %s" % err)
        if po.returncode != 0:
            raise SshClientException(out + err)
        else:
            return out # + err

    def upload_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp',
                   '-o', 'UserKnownHostsFile=/dev/null',
                   '-o', 'StrictHostKeyChecking=no',
                   '-o', 'ConnectTimeout=%d' % (self.ssh_connect_timeout),
                   '-i', self.key_fname] + extra_scp_args + \
                   [local_fname, '%s:%s' % (self.user, remote_fname)]
        scp_cmd_string = ' '.join(scp_cmd)
        log(scp_cmd_string)
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise SshClientException('scp failed: %s' % (output))
        else:
            return output

    def create_file(self, text, remote_fname):
        cmd = "cat <<DELIM > %s\n%s\nDELIM\n" % (remote_fname, text)
        self.cmd(cmd)

    def download_file(self, local_fname, remote_fname, extra_scp_args=[]):
        scp_cmd = ['scp',
                   '-o', 'UserKnownHostsFile=/dev/null',
                   '-o', 'StrictHostKeyChecking=no',
                   '-o', 'ConnectTimeout=%d' % (self.ssh_connect_timeout),
                   '-i', self.key_fname] + extra_scp_args + \
                       ['%s:%s' % (self.user, remote_fname), local_fname]
        scp_cmd_string = ' '.join(scp_cmd)
        log(scp_cmd_string)
        status, output = commands.getstatusoutput(scp_cmd_string)
        if status != 0:
            raise SshClientException('scp failed: %s' % (output))
        else:
            return output

    def find_file(self, remote_path):
        cmd = 'ls %s' % remote_path
        try:
            self.cmd(cmd)
        except SshClientException:
            return False
        return True
