#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
cgitb.enable()
import sys

import common
from common import ConfigsDb, authorize

email = authorize()

form = cgi.FieldStorage()
common.print_http_header()

cdb = ConfigsDb(email)
configs_json_str = cdb.get_configs_as_json()


values = {'configs_json_str': configs_json_str}

template = """
<html>
<title>Launch a new machine</title>

<script>

var machine_configurations = %s;


</script>

<script>

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

function log_to_div(div_name, message)
{
   document.getElementById(div_name).innerHTML += message +"<br>"; 
}

function launch(machine_config)
{
    // alert(machine_config + " ... seriously? ");
    machine_index = 0;
    
    var stream_url = '/cloudsim/inside/cgi-bin/machine_stream.py?machine_config=' + get_selectected_machine_index();
    var es = new EventSource(stream_url);
    
    es.addEventListener("action", function(event)
     {
         var str_data = event.data;
         log_to_div("machine_div_" + machine_index, "<b>action</b> " + str_data);
         
         
     }, false);    

    es.addEventListener("done", function(event)
    {
        es.close();
    },false);
        
        
}


function body_load()
{
    
    log_to_div("log_div", "<b>body_load</b><p>");
    var config_select = document.getElementById("config_select");
    var opts = config_select.options;
     
    for(var configuration in machine_configurations)
    {
        var opt = new Option(configuration);
        opts.add(opt);
    }
}

function clear_machine_log(div_name)
{
    var log_div = document.getElementById(div_name);
    log_div.innerHTML = "";
    
}
    
</script>


<body onload="body_load()">

<h1>Launch a new machine asynchronously</h1>
<p><b>Usage charges accumulate from the time the machine is launched.</b></p>


<select name="drop" id="config_select" >
</select>

<button type="button" onclick="launch(get_selectected_machine_config())">Launch machine</button>

<div id="machines">
    <h2>Machine 0 log<button type="button" onclick="clear_machine_log('machine_div_0')">Clear</button></h2>
    <div id="machine_div_0"></div>
</div>

<h2>Page log here</h2>
<div id="log_div"></div>

<form action=\"/cloudsim/inside/cgi-bin/machine_dolaunch.py\" method=\"GET\">
    <input type=\"submit\" value=\"Launch New Simulation Machine\"/> (type cg1.4xlarge, zone US East, <b>$2.10/hour</b>)
    <input type=\"hidden\" name=\"instance_type\" value=\"cg1.4xlarge\"/>
    <input type=\"hidden\" name=\"image_id\" value=\"ami-98fa58f1\"/>
    <input type=\"hidden\" name=\"zone\" value=\"useast\"/>
</form>
</body>

</html>
"""

#values = {'configs_json_str': configs_json_str}
#template = """
#<h1>ho</h1>
#var machine_configurations = {configs_json_str};
#
#"""


page = template % configs_json_str
print(page)

common.print_footer()
