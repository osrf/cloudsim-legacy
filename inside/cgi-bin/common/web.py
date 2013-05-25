import os
import sys


import tempfile
import Cookie
import json
import unittest


## web, logout, usercheck
OPENID_SESSION_COOKIE_NAME = 'open_id_session_id'
## web, usercheck
HTTP_COOKIE = 'HTTP_COOKIE'

ADMIN_EMAIL = 'cloudsim-info@osrfoundation.org'
USER_DATABASE = '/var/www-cloudsim-auth/users'
SESSION_DATABASE = '/var/www-cloudsim-auth/sessions'



def user_to_domain(email):
    d = email.split('@')[1]
    return d

class UserDatabase (object):
    def __init__(self, fname = USER_DATABASE):
        self.fname = fname
        if not os.path.exists(self.fname):
            self._write_users({})
        
    def get_users(self):    
        
        users = {}
        if os.path.exists(self.fname):
            with open(self.fname, 'r') as f:
                users = json.load(f)
        return users    
    
    def has_role(self, email, minimum_role):
        role = self.get_role(email)
        roles = ["user", "officer", "admin"]
        if roles.index(role) >= roles.index( minimum_role):
            return True
        return False
        
    def get_role(self, email):
        role = self.get_users()[email]
        return role
    
#    def is_admin(self, email):
#        admin = self.get_role(email) == "admin"
#        return admin
    
    def get_domain(self, email):
        d = user_to_domain(email)
        return d
    
    
    def add_user(self, email_address, role):
        users = self.get_users()
        new_guy = email_address.strip()
        if not new_guy in users:
            users[new_guy] = role
            self._write_users(users)
            
    def _write_users(self, users):
        with open(self.fname, 'w') as fp:
            json.dump(users, fp)

                   
    def remove_user(self, email_address):
        old_guy = email_address.strip()
        users = self.get_users()
        if old_guy in users:
            del users[old_guy]
            self._write_users(users)


class SessionDatabase(object):
    def __init__(self, fname=SESSION_DATABASE):
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
    print("Content-Type: application/octet-stream; name=\"%s\""%(fname))
    print("Content-Disposition: attachment; filename=\"%s\""%(fname))
    if newline:
        print("\n")


class AuthException(Exception):
    pass


def _check_auth(minimum_role):
    # Get session ID from cookie
    in_cookies = Cookie.Cookie()
    in_cookies.load(os.environ[HTTP_COOKIE])
    if OPENID_SESSION_COOKIE_NAME in in_cookies:
        openid_session = in_cookies[OPENID_SESSION_COOKIE_NAME].value
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

    lower_case_email = email.lower()
    lower_case_users =  [x.lower().strip() for x in users] 

    if lower_case_email not in lower_case_users:
        raise AuthException("Access denied (email address %s not found in db)"%(email) )
    if not udb.has_role(email, minimum_role):
        raise AuthException("Access denied (%s has insufficient privileges)" %(email) )
    return email


def authorize(minimum_role = "user"):


    email = None
    try:
        email = _check_auth(minimum_role)

    except AuthException as e:
        print_http_header()
        print("<title>Access Denied</title>")
        print("<h1>Access Denied</h1>")
        print("<h2>%s</h2>" % e)

        print("Try <a href=\"/cloudsim/inside/cgi-bin/logout\">logging out</a>.  For assistance, contact <a href=mailto:%s>%s</a>"%(ADMIN_EMAIL, ADMIN_EMAIL))
        exit(0)
    return email

def get_cloudsim_version_txt():
    d = os.path.split(__file__)[0]
    version_path = os.path.join(d,'..','..', '..','VERSION')
    if(os.path.exists(version_path)):
        with  open(version_path, 'r') as f:
            version = f.readlines()[0]
            return version 
    else:
        return "No version information available" 

def get_javascripts(exclude_list=[]):
    
    current = os.path.split(__file__)[0]
    script_dir = os.path.join(current,'..','..','..','js')
    script_dir = os.path.abspath(script_dir)
    files = os.listdir(script_dir)
    scripts = []
    s = '<script language="javascript" type="text/javascript" src="/js/'
    for f in files:
        if f.endswith('.js'):
            if f not in exclude_list:
                scripts.append(s + f + '"></script>')
    return '\n'.join(scripts)

#########################################################################
    
   
class CloudsimTest(unittest.TestCase):
    
    def test_version_str(self):
        s = get_cloudsim_version_txt()
        print(s)
        self.assert_(s != "No version information available", "versions")
    
    def test_javascripts(self):
        includes = get_javascripts()
        print(includes)


class AdminDbTest(unittest.TestCase):

    def test_addremove_users(self):
        db_fname = "userdbtest.txt" #get_test_path('userdbtest.txt')
        if(os.path.exists(db_fname)):
            os.remove(db_fname)
        
        db = UserDatabase(db_fname)
        users = db.get_users()
        
        # If test failed previously, the db may not be empty
        
        db.add_user('toto@popo.com', 'admin')
        self.assert_(len(db.get_users()) == 1, "not added!")
        self.assert_(db.get_users().keys()[0] == 'toto@popo.com', "wrong guy!")
        self.assert_(db.get_users()['toto@popo.com'] == 'admin', "wrong type o guy!")
        db.remove_user('not_a_real_user@popo.com')
        self.assert_(len(db.get_users()) == 1, "not not removed!")
        db.remove_user('toto@popo.com')
        self.assert_(len(db.get_users()) == 0, "not removed!")
        

         
        
if __name__ == '__main__':
    print('web TESTS')
    unittest.main()    
