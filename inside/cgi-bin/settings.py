#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header
cgitb.enable()


email = authorize("admin")
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)



version = get_cloudsim_version_txt()

user = {'user':email, 'role':'admin'}

user_info = json.dumps(user)
scripts = get_javascripts(['jquery-1.8.3.min.js'])

print_http_header()

page =  """<!DOCTYPE html>
<html>
 <head>
 
   <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
   <title>Settings</title>

    
   <link href="/js/layout.css" rel="stylesheet" type="text/css">
   <link rel="stylesheet" href="/js/jquery-ui.css" />

   <script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>

""" + scripts +"""
    
<script language="javascript">

    function on_load_page()
    {        
        $('.admin_only').show();
        
        add_osrf_cloud_credentials_widget("osrf_credentials_div");
        add_cloud_credentials_widget("amazon_credentials_div");
        add_users_admin_widget("users_div");
        
        setTimeout(users_update , 500);        
    }
    
    function users_update()
    {
        try
        {
            var callback = function(str_data)
            {
                var users = eval( '(' + str_data + ')' );
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

Welcome, """ + email + """ | <a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none; padding: 20px 0px 0px 0px;" align="right">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
    <a href="/cloudsim/inside/cgi-bin/console">Back to the console</a><br>
</div>
</div>    


<div style="width:100%; float:left;"><br><hr><br></div>

    <div class="admin_only" style="display:none;" >

        <div id="osrf_credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">            
        </div>
        
        <div id="amazon_credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2; ">            
        </div>
        
        <div id="users_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
        </div>

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