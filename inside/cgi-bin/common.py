from __future__ import print_function
import os
import tempfile
import Cookie
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
        self.openvpn_key_fname = os.path.join(self.path, OPENVPN_STATIC_KEY_FNAME)
        self.ssh_key_fname = os.path.join(self.path, 'key-%s.pem'%(self.name))


def list_machines(email):
    userdir = os.path.join(MACHINES_DIR, email)
    machines = []
    if os.path.isdir(userdir):
        for f in os.listdir(userdir):
            # TODO: error-check
            machines.append(Machine(f, os.path.join(userdir,f)))
    return machines
