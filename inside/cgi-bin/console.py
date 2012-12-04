#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import cgitb
import json
import os
from common import get_javascripts
cgitb.enable()

import common
from common import  authorize





email = authorize()
udb = common.UserDatabase()
role = udb.get_role(email)
user_info = json.dumps({'user':email, 'role':role})

scripts = get_javascripts(['machine_view.js', 'jquery-1.8.3.min.js', 'jquery.flot.js' ])

print("Content-Type: text/html")
print("\n")


# <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">



template = """ 
<!DOCTYPE html>
<html>
 <head>
 
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim console</title>
    <link href="/js/layout.css" rel="stylesheet" type="text/css">
    
    <script language="javascript" type="text/javascript" src="/js/jquery-1.8.3.min.js"></script>
    <script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>

""" + scripts +"""
    
    <script language="javascript" type="text/javascript" src="/js/latency_graph.js"></script>
    
    <script language="javascript">

    function on_load_page()
    {
        var user_info = """ + user_info + """;
        if(user_info.role == "admin")
        {
            $('.admin_only').show();
        }
        
        
        add_cloud_credentials_widget("credentials_div");
        add_users_admin_widget("users_div");
        
        machine_launch_on_load_page("launcher_div");
        add_constellations_widget("constellations_div");
        stream();
    }
    
    var log_events = true;
    
    function stream()
    {
        
        var stream_url = '/cloudsim/inside/cgi-bin/console_stream.py';
        console.log(stream_url);
        
        var es = new EventSource(stream_url);
        
        
        es.addEventListener("cloudsim", function(event)
        {
             var str_data = event.data;
             if(log_events)
                 console.log(str_data);
             var data = eval( '(' + str_data + ')' );
             $.publish("/cloudsim", data);
             
         }, false);
         
        es.addEventListener("done", function(event)
        {
            alert("Unexpected 'done' msg received");
            es.close();
        },false);
    }
    
    
    
    </script>
    
    
    
 </head>
    <body onload = "on_load_page()">
    
    <div class="admin_only" style="display:none;" >
        <div id="credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; ">
        </div>
        <div id="users_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; ">
        </div>
    </div>
    
    <div id="launcher_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px;  ">
    </div>
    
    <div id="constellations_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px;">
    </div>
    



<br>
<hr>
    <div style="float:right;">
        <img src="/js/images/osrf.png" width="200px"/>
        <!-- img src="/js/images/DARPA_Logo.jpg" width="200px"/ -->
    </div>

<div style="float:left;">

Logged in as: """ + email + """<br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none;">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
</div>
</div>    
    
</body>
</html>

"""

page = template 
print(page )
