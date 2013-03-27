#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header
cgitb.enable()

'''# --- usercheck

import sys
import Cookie
import cgi
import common

import cgitb
cgitb.enable()

EMAIL_VARNAME = 'openid.ext1.value.email'

# Get form and cookie data
form = cgi.FieldStorage()
email = form.getfirst(EMAIL_VARNAME)
in_cookies = Cookie.Cookie()
in_cookies.load(os.environ[common.HTTP_COOKIE])
openid_session = in_cookies[common.OPENID_SESSION_COOKIE_NAME].value

sdb = common.SessionDatabase()
sdb.load()

# Check email 
udb = common.UserDatabase()
users = udb.get_users()
print (users)

if not email:
    if openid_session in sdb.db:
        email = sdb.db[openid_session]
        
if email not in users:
    
    # print ("openid_session %s" % openid_session)
    if email:
        common.print_http_header()
        print("Access Denied ... '%s' not in users<br>" % (email))
        sys.exit(0)
    else:
        
        out_cookies = Cookie.SmartCookie()
        out_cookies[common.OPENID_SESSION_COOKIE_NAME] = ''
        out_cookies[common.OPENID_SESSION_COOKIE_NAME]['path'] = '/cloudsim/inside/cgi-bin/'
        print(out_cookies)
        common.print_http_header()
        print("""
        Your open session ID is not associated with a user. Please login again<br>
        <a href="/cloudsim/login.html">login</a>
        """)
        sys.exit(0)
    

    
# Save session ID and email to our own database

sdb.db[openid_session] = email
sdb.save()

# --- usercheck'''


email = authorize()
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)
version = get_cloudsim_version_txt()

user_info = json.dumps({'user':email, 'role':role})
scripts = get_javascripts(['machine_view.js', 'jquery-1.8.3.min.js', 'jquery.flot.js' ])

print_http_header()

page =  """<!DOCTYPE html>
<html>
 <head>
 
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim console</title>


    
<link href="/js/layout.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/js/jquery-ui.css" />


<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/jquery-ui.min.js"></script>

<script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>


""" + scripts +"""
    
    
<script language="javascript">

    function on_load_page()
    {
        var user_info = """ + user_info + """;
        if(user_info.role == "admin")
        {
            $('.admin_only').show();
        }
        
        // create_server_monitor_widget("server_monitor_div");
        add_cloud_credentials_widget("credentials_div");
        add_users_admin_widget("users_div");
        
        create_constellation_launcher_widget("launcher_div");
        create_constellations_widget("constellations_div");
        
        setTimeout(constellation_update , 500);
        setTimeout(users_update , 1500);
        
    }
    
    function users_update()
    {
        try
        {
            var callback = function(str_data)
            {
                var users = eval( '(' + str_data + ')' );
                $.publish('/users',users);
                setTimeout(users_update , 1500);
            };
        }
        catch(err)
        {
            console.log("update error: " + err.messagae);
        }
        async_get_users(callback);
    }
    
    function constellation_update()
    {
        try
        {
            console.log("update");
            
            var callback = function(str_data)
            {
               var constellations = eval( '(' + str_data + ')' );
               for (var i=0; i< constellations.length; i++)
               {
                   var constellation = constellations[i];
                   $.publish("/constellation" , constellation);
               } 
               // that was fun, let's do it again in 500 ms
               setTimeout(constellation_update , 500);
            };
        }
        catch(err)
        {
            console.log("update error: " + err.messagae);
        }
        // lets do it when we get the constellations data
        async_get_constellations(callback);
    }
    </script>
    
    
    
</head>
<body onload = "on_load_page()">



    <div style="float:left;">
        <!-- img src="/js/images/osrf.png" width="200px"/ -->
        <img src="/js/images/CloudSim_Logo.png" width="200px"/>
        <div  id="server_monitor_div" style="float:left">
        
        <!-- img src="/js/images/DARPA_Logo.jpg" width="200px"/ -->
        <!-- HOLA -->
        
    </div>

<div style="float:right;">

Welcome, """ + email + """<br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none;">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
</div>
</div>    


<div style="width:100%; float:left;"><br><hr><br></div>

    
    <div class="admin_only" style="display:none;" >

        <div id="credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">
        </div>

        <div id="users_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
        </div>

    </div>
        

    
    <div id="launcher_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px;  background-color:#f1f1f2;">
    </div>
    
    <div id="constellations_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
    </div>


<div id="footer" style="width:100%; float:left; ">



    
    <br>
    <hr>
    
    <div style="width:50%; float:left; margin-top:5px;">
            CloudSim Version """ + version + """
    </div>
    
    <div style="width:50%; float:right; " align="right">
     <img src="/js/images/osrf-pos-horz-cmyk.png" height="30px"/>
    </div>
</div>




    
</body>
</html>

"""

print(page)