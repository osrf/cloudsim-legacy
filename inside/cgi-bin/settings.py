#!/usr/bin/env python

from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header, get_auth_type

cgitb.enable()

email = authorize("officer")
udb = UserDatabase()
role = udb.get_role(email)

method = os.environ['REQUEST_METHOD']
if method != 'GET':
    exit(0)


version = get_cloudsim_version_txt()

# Authentication type (Basic or OpenId)
auth, _ = get_auth_type()

user = {'user': email,
        'role': role,
        'auth_type': auth}

 
user_info = json.dumps(user)
scripts = get_javascripts(['jquery-1.8.3.min.js'])

print_http_header()

page = """<!DOCTYPE html>
<html>
 <head>
 
   <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
   <title>Settings</title>

    
   <link href="/js/layout.css" rel="stylesheet" type="text/css">
   <link rel="stylesheet" href="/js/jquery-ui.css" />

   <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>



""" + scripts + """

<script language="javascript">

    function get_user_info()
    {
       var user_info = """ + user_info + """;
       return user_info; 
    }

    function on_load_page()
    {
        var user_info = get_user_info();
        console.log("User role: " +  user_info.role);
        if(user_info.role == "admin")
        {
            $('.admin_only').show();
            add_osrf_cloud_credentials_widget("osrf_credentials_div");
            add_cloud_credentials_widget("amazon_credentials_div");
            add_portal_settings_widget("portal_settings_div");
        }
        add_users_admin_widget("users_div", user_info.auth_type);
        setTimeout(users_update , 500);
    }

    function users_update()
    {
        try
        {
            var callback = function(data)
            {
                var users = data;
                $.publish('/users',users);
                setTimeout(users_update , 500);
            };
        }
        catch(err)
        {
            console.log("update error: " + err.messagae);
        }
        async_get_users(callback);
    }
</script>

</head>
<body onload = "on_load_page()">

    <div style="float:left;">
        <img src="/js/images/CloudSim_Logo.png" width="200px"/>
        <div  id="server_monitor_div" style="float:left">
    </div>

<div style="float:right;">

Welcome, """ + email + """ <br>

<div class="admin_only"
     style="display: none; padding: 0px 0px 0px 0px;"
     align="right">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>

</div>
    <div style="padding:0px 0px 0px;" align="right">
    <a href="/cloudsim/inside/cgi-bin/console">Back to the console</a><br>
    </div>

    <div style="padding:0px 0px 0px;" align="right">
    <a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
    </div>

</div>


<div style="width:100%; float:left;"><br><hr><br></div>

    <div class="admin_only" style="display: none;" >

        <div id="osrf_credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">            
        </div>

        <div id="amazon_credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">            
        </div>

        <div id="portal_settings_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">            
        </div>

    </div>

        <div id="users_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
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