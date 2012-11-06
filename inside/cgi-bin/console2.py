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

common.print_http_header() 

cdb = ConfigsDb(email)
configs_json_str = cdb.get_configs_as_json()

mdb = MachineDb(email)
machines_json_str = mdb.get_machines_as_json() 
    

form = cgi.FieldStorage()
action = form.getfirst("action", "" )
machine_type = form.getfirst('machine_type', "")


local_script = """

<script>
action = "%s";
machine_type = "%s";
machine_configurations = %s;
machines = %s;
</script>

""" % (action, machine_type, configs_json_str, machines_json_str )


if action == "launch":
    import create_ec2_instance
    module_dir = os.path.dirname(create_ec2_instance.__file__)
    script = """#!/usr/bin/env python
    import sys
    sys.path.append('%s')
    import create_ec2_instance
    create_ec2_instance.create_ec2_instance('%s', '%s', instance_type='%s', image_id='%s')"""%(module_dir, botofile, os.path.join(common.MACHINES_DIR, domain), instance_type, image_id)
    common.start_background_task(script)

print(""" 

<html>
<title>Console</title>

%s

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


function get_config_names()
{
    
    var keys = [];
    for(var key in machine_configurations)
    {
        keys.push(key);
    }
    return keys;
}

function get_machine_names()
{
 
    var keys = [];
    for(var key in machines)
    {
            keys.push(key);
    }
    return keys;
}

function on_load_page()
{
   
    
    // add the configs to the launch type drop down menu
    
    log_to_div("log_div", "<b>body_load</b><p>");
    var config_select = document.getElementById("config_select");
    var opts = config_select.options;
     
    for(var configuration in machine_configurations)
    {
        var opt = new Option(configuration);
        opts.add(opt);
    }
    
  
    // list the configs available
    
    var s = "<h2>Configurations</h2>";
    var configs = document.getElementById("configs");
    var config_names = get_config_names();
    for (var i=0; i <  config_names.length; i++)
    {  
        s += config_names[i] + "<br>";
    }
    configs.innerHTML = s;

    
    // create a div for each running machines 
    var s = "<h2>Machines</h2>";
    var configs = document.getElementById("machines_div");
    var machine_names = get_machine_names();
    for (var i=0; i <  machine_names.length; i++)
    {  
        s += '<div id="' + machine_names[i] + '">';
        s += "<h3>name:" + machine_names[i] + "</h3>";
        s += '</div>';
    }
    configs.innerHTML = s;
    
    // stream info for each machine
    for (var i=0; i <  machine_names.length; i++)
    {
        var machine_name = machine_names[i];
        stream(machine_name);
    }
    
    
}

function stream(machine_name)
{
    var machine_div_name = machine_name ;
    var stream_url = '/cloudsim/inside/cgi-bin/machine_stream_launch.py?machine_name=' + machine_name;
    log_to_div(machine_div_name, stream_url);
    
    var es = new EventSource(stream_url);
    
    es.addEventListener("action", function(event)
    {
         var str_data = event.data;
         log_to_div(machine_div_name, "<b>action</b> " + str_data);
         
     }, false);    

    es.addEventListener("check", function(event)
    {
         var str_data = event.data;
         log_to_div(machine_div_name, "<b>check</b> " + str_data);
         
     }, false);    

    es.addEventListener("retry", function(event)
    {
         var str_data = event.data;
         log_to_div(machine_div_name, "<b>retry</b> " + str_data);
         
     }, false);    
         
    es.addEventListener("done", function(event)
    {
        es.close();
    },false);
}

function launch(machine_config)
{
    // alert(machine_config + " ... seriously? ");
    machine_index = 0;
    var machine_div_name =  "machine_div_" + machine_index;

    var r=confirm("Launch?");
    if (r==false)
    {
        x="You pressed Cancel!";
        return;
    }

    // window.location.href = "/cloudsim/inside/cgi-bin/console2.py";
    
    var stream_url = '/cloudsim/inside/cgi-bin/machine_stream.py?machine_config=' + get_selectected_machine_config();
    log_to_div(machine_div_name, stream_url);
    
    var es = new EventSource(stream_url);
    
    es.addEventListener("action", function(event)
     {
         var str_data = event.data;
         log_to_div(machine_div_name, "<b>action</b> " + str_data);
         
         
     }, false);    

    es.addEventListener("done", function(event)
    {
        es.close();
    },false);

    
}

function clear_machine_log(div_name)
{
    var log_div = document.getElementById(div_name);
    log_div.innerHTML = "";
    
}

function check_before_launch()
{

 // form onSubmit="return check_before_launch()"
 
    var x;
    var r=confirm("Launch?");
    if (r==true)
    {
        x="You pressed OK!";
        
    }
    else
    {
        x="You pressed Cancel!";
        
    }
    return r;
}

</script>

<body onload = "on_load_page()">
<h1>Console2</h1>
<div id='configs'></div>
<div id='machines_div'></div>
<br>

<h2>Launch a new machine asynchronously</h2>
<p><b>Usage charges accumulate from the time the machine is launched.</b></p>

<!-- 
<form action="/cloudsim/inside/cgi-bin/console2.py" method="GET">
    <select name="machine_type" id="config_select" ></select>
    <button type="submit" >Launch machine</button>
    <input type=\"hidden\" name=\"action\" value=\"launch\" />
</form>

-->



<select id="config_select" ></select>
<button type="button" onclick="launch(get_selectected_machine_config())">Launch2</button>

<br>
<div id="machines_div">
    <h2>Machine 0 log<button type="button" onclick="clear_machine_log('machine_div_0')">Clear</button></h2>
    <div id="machine_div_0"></div>
</div>


<h2>Page log here</h2>
<div id="log_div"></div>

<br>
<a href="/cloudsim/inside/cgi-bin/logout.py">Logout</a>
</body>
</html>
""" % (local_script) )
    

    