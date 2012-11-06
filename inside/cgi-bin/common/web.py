import os
import sys
import cgi
import common
import tempfile
import Cookie
import time

class UserDatabase (object):
    def __init__(self, fname = common.USER_DATABASE):
        self.fname = fname
        if not os.path.exists(self.fname):
            self._write_users([])
        
    def get_users(self):    
        
        users = []
        if os.path.exists(self.fname):
            with open(self.fname, 'r') as f:
                for u in f.readlines():
                    users.append(u.strip())
                f.close()
        return users    
    
    def add_user(self, email_address):
        users = self.get_users()
        new_guy = email_address.strip()
        if not new_guy in users:
            users.append(new_guy)
            self._write_users(users)
            
    def _write_users(self, users):
        with open(self.fname, 'w') as f:
            for u in users:
                f.write("%s\n" % u)
            f.close()
                
    def remove_user(self, email_address):
        old_guy = email_address.strip()
        users = self.get_users()
        if old_guy in users:
            users.remove(old_guy)
            self._write_users(users)


class SessionDatabase(object):
    def __init__(self, fname=common.SESSION_DATABASE):
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

def print_http_filedownload_header(fname, newline=True):
    print("Content-Type: applicatoin/octet-stream; name=\"%s\""%(fname))
    print("Content-Disposition: attachment; filename=\"%s\""%(fname))
    if newline:
        print("\n")


def session_id_to_email():
    in_cookies = Cookie.Cookie()
    in_cookies.load(os.environ[common.HTTP_COOKIE])
    # Check for a session cookie
    # print("in_cookies %s<p>" % in_cookies)
    
    if common.OPENID_SESSION_COOKIE_NAME in in_cookies:
        session_id = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value
        sdb = SessionDatabase(common.SESSION_DATABASE)
        if session_id in sdb.db:
            email = sdb.db[session_id]
            return email
    return None

def print_footer():
    email = session_id_to_email()
    print("<hr>")
    print("Logged in as: %s<br>"%(email))
    print("<a href=\"/cloudsim/inside/cgi-bin/admin.py\">Admin</a><br>")
    print("<a href=\"/cloudsim/inside/cgi-bin/console_old.py\">Console</a><br>")
    print("<a href=\"/cloudsim/inside/cgi-bin/logout.py\">Logout</a>")
 

class AuthException(Exception): pass

def _check_auth():
    # Get session ID from cookie
    in_cookies = Cookie.Cookie()
    in_cookies.load(os.environ[common.HTTP_COOKIE])
    if common.OPENID_SESSION_COOKIE_NAME in in_cookies:
        openid_session = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value
    else:
        raise  AuthException("Access denied (no session ID found in cookies)")
        sys.exit(0)
    
    # Convert session ID to email
    sdb = SessionDatabase()
    if openid_session in sdb.db:
        email = sdb.db[openid_session]
    else:
        raise AuthException("Access denied (session ID %s not found in db)"%(openid_session))
    
    # Compare email to user db
    udb = UserDatabase()
    users = udb.get_users()
    if email not in users:
        raise AuthException("Access denied (email address %s not found in db)"%(email) )
    
    return email
   



def check_auth_and_generate_response():
    
    email = None
    try:        
        email = _check_auth()
        return True
    
    except AuthException as e:
        print_http_header()
        print("<title>Access Denied</title>")
        print("<h1>Access Denied</h1>")
        
        print("<h2>%s</h2>" % e)
           
        print("Try <a href=\"/cloudsim/inside/cgi-bin/logout.py\">logging out</a>.  For assistance, contact <a href=mailto:%s>%s</a>"%(common.ADMIN_EMAIL, common.ADMIN_EMAIL))
        exit(0)
 
 
        
def authorize():
    email = None
    try:        
        email = _check_auth()
        return email
    
    except AuthException as e:
        print_http_header()
        print("<title>Access Denied</title>")
        print("<h1>Access Denied</h1>")
        
        print("<h2>%s</h2>" % e)
           
        print("Try <a href=\"/cloudsim/inside/cgi-bin/logout.py\">logging out</a>.  For assistance, contact <a href=mailto:%s>%s</a>"%(common.ADMIN_EMAIL, common.ADMIN_EMAIL))
        exit(0)     
        
               
def tail(fname):
    file = open(fname,'r')
    
    for l in file.readlines():
        sys.stdout.write (l)
        sys.stdout.flush()
    
#    file.close()
#    return
    
    while 1:
        where = file.tell()
        line = file.readline()
        if not line:
            time.sleep(1)
            file.seek(where)
        else:
            print line    
            sys.stdout.flush()
    # todo: close file at some point