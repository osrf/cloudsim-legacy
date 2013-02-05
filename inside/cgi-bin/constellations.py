#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
import os
cgitb.enable()

from common import  authorize

email = authorize()
method = os.environ['REQUEST_METHOD']

print('Content-type: application/json')
print("\n")

if method != 'GET':
    return

email = authorize()
udb = common.UserDatabase()
role = udb.get_role(email)
version = common.get_cloudsim_version_txt()

user_info = json.dumps({'user':email, 'role':role})
scripts = get_javascripts(['machine_view.js', 'jquery-1.8.3.min.js', 'jquery.flot.js' ])

page =  """Content-Type: text/html


<!DOCTYPE html>
<html>
 <head>
 
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim console</title>


    
<link href="/js/layout.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/js/jquery-ui.css" />


<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.2/jquery-ui.min.js"></script>

<script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>


""" + scripts +"""
    
    
<script language="javascript">

    function on_load_page()
    {
        var user_info = """ + user_info + """;
        
        create_constellation_launcher_widget("launcher_div");
        create_constellations_widget("constellations_div");
        
        update();
    }
    
    var log_events = true;
    
    function update()
    {
        
        var update_url = '/cloudsim/inside/cgi-bin/console_stream.py';
        console.log(stream_url);
        
        var es = new EventSource(stream_url);
        
        var hidden_event_types = [];
        
        es.addEventListener("cloudsim", function(event)
        {
             var str_data = event.data;
             var data = eval( '(' + str_data + ')' );
             
             if(log_events)
             {
                 var type = data.type;
                 // console.log(type);
                 if( hidden_event_types.indexOf(type) == -1) 
                 {
                     console.log(str_data);
                 }
             }
             
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



    <div style="float:left;">
        <img src="/js/images/osrf.png" width="200px"/>
        <!-- img src="/js/images/DARPA_Logo.jpg" width="200px"/ -->
        
    </div>

<div style="float:right;">

Welcome, """ + email + """<br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none;">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
</div>
</div>    


<div style="width:100%; float:left;"><br><hr><br></div>
    
    
    <div id="launcher_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px;  background-color:#f1f1f2;">
    </div>
    
    <div id="constellations_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
    </div>

    <div> 
    </div>
    
<div id="footer" style="width:100%; float:left; ">
<br>
<hr>
<i>    <div id="server_monitor_div" style="float:left"></div> CloudSim """ + version + """ is provided by the <b>Open Source Robotics Foundation</b>. (Your frame rate may vary. Electric sheep not included)</i>
</div>
    
</body>
</html>

"""

print(page)