class Provider(object):
    def __init__(self):
        self.ssh_private_key = None
        self.username = None
        self.hostname = None

    def test_ssh(self, timeout=1, fname='/etc/issue'):
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'ls', fname]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)
