#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import sys
import os
import Cookie
import time

import cgi
import cgitb
cgitb.enable()

import common
from common import  authorize, ConfigsDb, MachineDb

email = authorize()

print("Content-Type: text/html")
print("\n")



template = """ 
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">
<html>
 <head>
 
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim console</title>
    <link href="/js/layout.css" rel="stylesheet" type="text/css">


    <script src="/js/machine_ui_view.js"></script>
    <script src="/js/machine_launch.js"></script>
    <script src="/js/utils.js"></script>
  
    <script language="javascript" type="text/javascript" src="/js/graph/jquery.js"></script>
    <script language="javascript" type="text/javascript" src="/js/graph/jquery.flot.js"></script>
    
    <script language="javascript" type="text/javascript" src="/js/latency_graph.js"></script>
    
    <script language="javascript">
    
    function on_load_page()
    {
        machine_view_on_load_page("machines_div");
        machine_launch_on_load_page("launcher_div");
        stream();
    }
    
    
    function stream()
    {
        var div_name = "machines_log_div";
        var stream_url = '/cloudsim/inside/cgi-bin/console_stream.py';
        
        log_to_div(div_name, '<b>stream url:</b>' + stream_url);
        
        var es = new EventSource(stream_url);
        
        es.addEventListener("cloudsim", function(event)
        {
             var str_data = event.data;
             machine_view_status_event("machines_div", str_data );
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

    <h2>Launcher</h2>
    <div id="launcher_div" style="width:100%; float:left; border: 1px solid black; margin: 2px; padding: 2px;">
    </div>
    <h2>Machines</h2>
    <div id="machines_div" style="width:100%; float:left; border: 1px solid black; margin: 5px; padding: 5px;">
    </div>
    
    <h2>Log</h2>
    <button type="button" onclick="clear_div('log_div')">clear</button>
    <div id="log_div"></div>


</script>


<br>
<a href="/cloudsim/inside/cgi-bin/admin.py">Admin</a><br>
<a href="/cloudsim/inside/cgi-bin/logout.py">Logout</a>
</body>
</html>



"""


page = template
print(page )
