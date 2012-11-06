#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function

import sys
import os

from common import  authorize, ConfigsDb, MachineDb, print_http_header

import cgi
import cgitb
cgitb.enable()


email = authorize()
mdb = MachineDb(email)

print_http_header()

javascript = """


function httpGet(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}


function log_to_div(div_name, message)
{
   document.getElementById(div_name).innerHTML += message +"<br>"; 
}


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

function clear_div(div_name)
{
   document.getElementById(div_name).innerHTML = "";  
}

"""


template = """ 

<html>
<head>
<title>Console</title>
<script src="/js/machine_view.js"></script>
<script src="/js/machine_launch.js"></script>
<script>
%s
</script>
</head>


<body onload = "on_load_page()">
<h1>Console</h1>

<h2>Launcher</h2>

<div id="launcher_div" style="border: 1px solid black; margin: 2px; padding: 2px;">
    <select id="config_select" onchange="launchSelectionChanged()";></select>
    <button type="button" onclick="launch(get_selectected_machine_config())">Launch</button>
    <div id="config_div"></div>
</div>

<h2>Machines</h2>

<div id="machines_div" style="border: 1px solid black; margin: 5px; padding: 5px;">
    
    
    
</div>


<h2>Log</h2>
<button type="button" onclick="clear_div('log_div')">clear</button>
<div id="log_div"></div>

<br>
<a href="/cloudsim/inside/cgi-bin/admin.py">Admin</a><br>
<a href="/cloudsim/inside/cgi-bin/logout.py">Logout</a>
</body>
</html>
"""


page = template % ( javascript)
print(page )