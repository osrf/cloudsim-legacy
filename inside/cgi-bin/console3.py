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


var machine_configurations = null;

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
    var div_name = "log_div";
    log_to_div(div_name, "on_load_page");
    
    var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs.py");
    machine_configurations = eval( '(' + x + ')' );
    
    var config_select = document.getElementById("config_select");
    var opts = config_select.options;
    
    for(var configuration in machine_configurations)
    {
        // log_to_div(div_name, "<b>config:</b> " + configuration);
        var opt = new Option(configuration);
        opts.add(opt);
    }
    launchSelectionChanged()
    
    stream();
}


// =====================================
function launch(machine_config)
{
    machine_index = 0;
    var machine_div_name =  "machine_div_" + machine_index;

    var r=confirm("Launch?");
    if (r==false)
    {
        // x="You pressed Cancel!";
        return;
    }

    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=launch&machine_config=' + get_selectected_machine_config();
    log_to_div("log_div", url);
    msg = httpGet(url)
    //alert(msg);
    log_to_div("log_div", "\\n");
    log_to_div("log_div", msg);
}

function get_selectected_machine_index()
{
    var i =document.getElementById("config_select").selectedIndex;
    return i;
}

function get_selectected_machine_config()
{
    var i =get_selectected_machine_index();
    var machine_config =document.getElementById("config_select").options[i].text;
    return machine_config;
}

function launchSelectionChanged()
{

    var machine_config =get_selectected_machine_config();
    var conf = machine_configurations[machine_config];
    
    var str = "distro " + conf.distro + "<br>";
    str += "instance_type " + conf.instance_type + "<br>";
    str += "image_id " + conf.image_id + "<br>";
    
    document.getElementById("config_div").innerHTML = str;
}

function stream()
{
    div_name = "log_div";
    var stream_url = '<b>stream url:</b> /cloudsim/inside/cgi-bin/console_stream.py';
    
    log_to_div(div_name, stream_url);
    
    var es = new EventSource(stream_url);
    
    es.addEventListener("cloudsim", function(event)
    {
         var str_data = event.data;
         log_to_div(div_name, "<b>event</b> " + str_data);
         
     }, false);
     
     
    es.addEventListener("done", function(event)
    {
        es.close();
    },false);
}

"""


template = """ 

<html>
<title>Console</title>



<script>
%s
</script>

<body onload = "on_load_page()">
<h1>Console 3</h1>

<select id="config_select" onchange="launchSelectionChanged()";></select>
<button type="button" onclick="launch(get_selectected_machine_config())">Launch</button>
<div id="config_div"></div>
<div id="machines_div"></div>
<h2>Log</h2>
<div id="log_div"></div>

<br>
<a href="/cloudsim/inside/cgi-bin/logout.py">Logout</a>
</body>
</html>
"""


page = template % ( javascript)
print(page )