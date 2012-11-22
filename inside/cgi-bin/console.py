#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import cgitb
import json
import os
cgitb.enable()

import common
from common import  authorize



def get_javascripts():
    
    current = os.path.split(__file__)[0]
    script_dir = os.path.join(current,'..','..','js')
    script_dir = os.path.abspath(script_dir)
    files = os.listdir(script_dir)
    scripts = []
    s = '<script language="javascript" type="text/javascript" src="/js/'
    for f in files:
        if f.endswith('.js'):
            scripts.append(s + f + '"></script>')
    return '\n'.join(scripts)

email = authorize()
udb = common.UserDatabase()
role = udb.get_role(email)
user_info = json.dumps({'user':email, 'role':role})

scripts = get_javascripts()

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
        machine_view_on_load_page("machines_div");
        machine_launch_on_load_page("launcher_div");
        cloud_credentials_on_load_page("credentials_div");
        users_admin_on_load_page("users_div");
        constellations_on_load_page("constellations_div");
        stream();
    }
    
    function stream()
    {
        
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
    
    var const_count = 0;
    function constellation_add_click(div_name)
    {
        const_count += 1;
        var constellation_name="const_"+const_count;
        constellation_add(div_name, constellation_name);
    }
    
    function constellation_remove_click(div_name)
    {
        var div = document.getElementById(div_name);
        var last_id = div.lastElementChild.id;
        // div.removeChild(last);
        constellation_remove(div_name, last_id);
        
    }
    
    var machine_count = 0;
    function machine_add_click(div_name)
    {
        machine_count +=1;
        var div = document.getElementById('add_machine');
        var constellation = div.querySelectorAll("input")[0].value;
        
        var machine_name = "mach_" + machine_count;
        machine_add(div_name, constellation, machine_name);
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
    
    <div id="machines_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px;">
    </div>
    
    <button onclick="constellation_add_click('constellations_div');">Add</button>
    <button onclick="constellation_remove_click('constellations_div');">Remove</button>
    <div id="add_machine">
        Constellation<input type="text" name="constellation"/>
        <button onclick="machine_add_click('constellations_div');">Add machine</button>
        <button onclick="machine_remove_click('constellations_div');">Remove machine</button>
    </div>
    
    <div id="constellations_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px;">
    </div>


<br>
<hr>
    <div style="float:right;">
        <img src="/js/images/osrf.png" width="200px"/>
        <img src="/js/images/DARPA_Logo.jpg" width="200px"/>
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
