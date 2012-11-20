import os
import sys

import common
import tempfile
import Cookie
import json


import unittest


class UserDatabase (object):
    def __init__(self, fname = common.USER_DATABASE):
        self.fname = fname
        if not os.path.exists(self.fname):
            self._write_users({})
        
    def get_users(self):    
        
        users = {}
        if os.path.exists(self.fname):
            with open(self.fname, 'r') as f:
                users = json.load(f)
                
#            with open(self.fname, 'r') as f:
#                for u in f.readlines():
#                    users.append(u.strip())
#                f.close()
        return users    
    
    def get_role(self, email):
        role = self.get_users()[email]
        return role
    
    def add_user(self, email_address, role):
        users = self.get_users()
        new_guy = email_address.strip()
        if not new_guy in users:
            users[new_guy] = role
            self._write_users(users)
            
    def _write_users(self, users):
        with open(self.fname, 'w') as fp:
            json.dump(users, fp)
#            for u in users:
#                f.write("%s\n" % u)
            
                
    def remove_user(self, email_address):
        old_guy = email_address.strip()
        users = self.get_users()
        if old_guy in users:
            del users[old_guy]
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
    print("<a href=\"/cloudsim/inside/cgi-bin/console.py\">Console</a><br>")
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
 
 
        
def authorize(role = "user"):
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
        

def get_cloudsim_verion_txt():
    d = os.path.split(__file__)[0]
    hg_log_path = os.path.join(d,'..','..', '..','hg_log.txt')
    if(os.path.exists(hg_log_path)):
        with  open(hg_log_path, 'r') as f:
                version = f.read()
                return version 
    return "No version information available" 

#########################################################################
    
   
class CloudsimTest(unittest.TestCase):
    
    def test_version_str(self):
        s = get_cloudsim_verion_txt()
        print(s)
        self.assert_(s != "No version information available", "versions")
        


class AdminDbTest(unittest.TestCase):

    def test_addremove_users(self):
        db_fname = common.get_test_path('userdbtest.txt')
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