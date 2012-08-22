from __future__ import print_function
import os
import tempfile
import subprocess
import Cookie
import boto
import cgi
import cgitb
cgitb.enable()

EMAIL_VARNAME = 'openid.ext1.value.email'
ADMIN_EMAIL = 'cloudsim-info@osrfoundation.org'
USER_DATABASE = '/var/www-cloudsim-auth/users'
SESSION_DATABASE = '/var/www-cloudsim-auth/sessions'
BOTO_CONFIG_FILE = '/var/www-cloudsim-auth/boto'
MACHINES_DIR = '/var/www-cloudsim-auth/machines'
OPENID_SESSION_COOKIE_NAME = 'open_id_session_id'
CLOUDSIM_SESSION_COOKIE_NAME = 'cloudsim_session_id'
HTTP_COOKIE = 'HTTP_COOKIE'
MACHINE_ID_VARNAME = 'machine_id'
OPENVPN_CONFIG_FNAME = 'openvpn.config'
OPENVPN_STATIC_KEY_FNAME = 'static.key'
HOSTNAME_FNAME = 'hostname'
USERNAME_FNAME = 'username'
AWS_ID_FNAME = 'aws_id'

def get_user_database():
    # Load user database
    users = []
    with open(USER_DATABASE, 'r') as f:
        for u in f.readlines():
            users.append(u.strip())
    return users

class SessionDatabase():
    def __init__(self, fname):
        self.db = {}
        self.fname = fname
        self.load()

    def load(self):
        self.db = {}
        if not os.path.isfile(self.fname):
            # Touch
            open(self.fname, 'w')    
        with open(self.fname, 'r') as f:
            for u in f.readlines():
                fields = u.split()
                if len(fields) == 2:
                    self.db[fields[0]] = fields[1]

    def save(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmpfile:
            tmpfname = tmpfile.name
            for k,v in self.db.iteritems():
                tmpfile.write("%s %s\n"%(k,v))
        os.rename(tmpfname, self.fname)

def print_http_header(newline=True):
    print("Content-Type: text/html")
    if newline:
        print("\n")

def session_id_to_email():
    in_cookies = Cookie.Cookie()
    in_cookies.load(os.environ[HTTP_COOKIE])
    # Check for a session cookie
    if CLOUDSIM_SESSION_COOKIE_NAME in in_cookies:
        cloudsim_session_id = in_cookies[CLOUDSIM_SESSION_COOKIE_NAME].value
        sdb = SessionDatabase(SESSION_DATABASE)
        if cloudsim_session_id in sdb.db:
            email = sdb.db[cloudsim_session_id]
            return email
    return None

def check_auth(check_email=False):
    email = None
    if check_email:
        form = cgi.FieldStorage()
        email = form.getfirst(EMAIL_VARNAME)
    if email:
        save_session_id = True
    else:
        email = session_id_to_email()
        save_session_id = False
    if email:
        users = get_user_database()
        if email in users:
            in_cookies = Cookie.Cookie()
            in_cookies.load(os.environ[HTTP_COOKIE])
            if save_session_id and OPENID_SESSION_COOKIE_NAME in in_cookies:
                cloudsim_session_id = in_cookies[OPENID_SESSION_COOKIE_NAME].value
                sdb = SessionDatabase(SESSION_DATABASE)
                sdb.db[cloudsim_session_id] = email
                sdb.save()
            return True
    return None

def check_auth_and_generate_response(check_email=False):
    if check_auth(check_email):
        return True
    else:
        print_http_header()
        print("<title>Access Denied</title>")
        print("<h1>Access Denied</h1>")
        print("Try <a href=\"/cloudsim/inside/cgi-bin/logout.py\">logging out</a>.  For assistance, contact <a href=mailto:%s>%s</a>"%(ADMIN_EMAIL, ADMIN_EMAIL))
        print("<hr>")
        C = Cookie.Cookie()
        C.load(os.environ[HTTP_COOKIE])
        print(C)
        print("<hr>")
        form = cgi.FieldStorage()
        print(form)
        print("<hr>")
        return False

def print_footer():
    email = session_id_to_email()
    print("<hr>")
    print("Logged in as: %s<br>"%(email))
    print("<a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a><br>")
    print("<a href=\"/cloudsim/inside/cgi-bin/logout.py\">Logout</a>")

class Machine:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.openvpn_config_fname = os.path.join(self.path, OPENVPN_CONFIG_FNAME)
        self.openvpn_config = open(self.openvpn_config_fname).read()
        self.openvpn_key_fname = os.path.join(self.path, OPENVPN_STATIC_KEY_FNAME)
        self.openvpn_key = open(self.openvpn_key_fname).read()
        self.ssh_key_fname = os.path.join(self.path, 'key-%s.pem'%(self.name))
        self.ssh_key = open(self.ssh_key_fname).read()
        self.hostname_fname = os.path.join(self.path, HOSTNAME_FNAME)
        self.hostname = open(self.hostname_fname).read().strip()
        self.username_fname = os.path.join(self.path, USERNAME_FNAME)
        self.username = open(self.username_fname).read().strip()
        self.aws_id_fname = os.path.join(self.path, AWS_ID_FNAME)
        self.aws_id = open(self.aws_id_fname).read().strip()

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
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'ls', fname]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def test_X(self, timeout=1):
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'DISPLAY=localhost:0', 'glxinfo']
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def reboot(self, timeout=1):
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-o', 'ConnectTimeout=%d'%(timeout), '-i', self.ssh_key_fname, '%s@%s'%(self.username, self.hostname), 'sudo', 'reboot']
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode == 0:
            return (True, out + err)
        else:
            return (False, out + err)

    def stop(self, timeout=1):
        ec2 = create_ec2_proxy(BOTO_CONFIG_FILE)
        try:
            ec2.stop_instances([self.aws_id])
        except Exception as e:
            return False
        return True

    def start(self, timeout=1):
        ec2 = create_ec2_proxy(BOTO_CONFIG_FILE)
        try:
            ec2.start_instances([self.aws_id])
        except Exception as e:
            return False
        return True

def create_ec2_proxy(boto_config_file):
    # Load boto config from indicated file.  By overwriting boto.config,
    # our new config will be used.
    boto.config = boto.pyami.config.Config(boto_config_file)

    # No args: uses config from boto.config
    ec2 = boto.connect_ec2()
    return ec2
        
def list_machines(email):
    userdir = os.path.join(MACHINES_DIR, email)
    machines = []
    if os.path.isdir(userdir):
        for f in os.listdir(userdir):
            try:
                machines.append(Machine(f, os.path.join(userdir,f)))
            except Exception as e:
                # Ignore corrupt machine directories
                pass
    return machines
