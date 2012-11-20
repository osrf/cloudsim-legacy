#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import sys
import os
import Cookie
import time

import cgi
import cgitb
import json
cgitb.enable()

import common
from common import  authorize

email = authorize()
udb = common.UserDatabase()
role = udb.get_role(email)

user_info = json.dumps({'user':email, 'role':role})

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
    
    <script language="javascript" type="text/javascript" src="/js/graph/jquery.js"></script>
    <script language="javascript" type="text/javascript" src="/js/graph/jquery.flot.js"></script>
    
    
    <script src="/js/utils.js"></script>

    <script src="/js/machine_ui_view.js"></script>
    <script src="/js/machine_launch.js"></script>\
    <div class="admin_only">
        <script src="/js/cloud_credentials.js"></script>
        <script src="/js/users_admin.js"></script>
    </div>
    
    
    <script language="javascript" type="text/javascript" src="/js/latency_graph.js"></script>
    
    <script language="javascript">

    function on_load_page()
    {
"""
template += "  var user_info = %s;" %  user_info

template +="""     
        if(user_info.role == "admin")
        {
            $('.admin_only').show();
        }
        machine_view_on_load_page("machines_div");
        machine_launch_on_load_page("launcher_div");
        cloud_credentials_on_load_page("credentials_div");
        users_admin_on_load_page("users_div");
        stream();
    }
    
    function stream()
    {
        var div_name = "log_div";
        var stream_url = '/cloudsim/inside/cgi-bin/console_stream.py';
        
        console.log(stream_url);
        
        var es = new EventSource(stream_url);
        
        es.addEventListener("cloudsim", function(event)
        {
             var str_data = event.data;
             machine_view_status_event("machines_div", str_data );
             users_admin_event(str_data);
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
    
    <div class="admin_only" style="display:none;">
        <div id="credentials_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; margin-top:20px; ">
        </div>
        <div id="users_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; margin-top:20px; ">
        </div>
    </div>
    
    <div id="launcher_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px; margin-top:20px; ">
    </div>
    
    <div id="machines_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px;">
    </div>
    
    
    
    <div style="display:none;">
    <h2 >Log</h2>
    <button type="button" onclick="clear_div('log_div')">clear</button>
    <div id="log_div"></div>
    </div>
    

<br>  """

template += """
<hr>
    <div style="float:right;">
        <img src="/js/images/osrf.png" width="200px"/>
        <img src="/js/images/DARPA_Logo.jpg" width="200px"/>
    </div>

<div style="float:left;">

Logged in as: %s <br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none;">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
</div>
</div>    
    
</body>
</html>

""" % email

page = template 
print(page )
