#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header
cgitb.enable()


email = authorize()
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)
version = get_cloudsim_version_txt()

user_info = json.dumps({'user':email, 'role':role})
scripts = get_javascripts(['jquery-1.8.3.min.js', 'jquery.flot.js' ])

print_http_header()

page =  """<!DOCTYPE html>
<html>
 <head>
 
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim console</title>


    
<link href="/js/layout.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/js/jquery-ui.css" />


<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/jquery-ui.min.js"></script>

<script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>


""" + scripts +"""
    
    
<script language="javascript">

    var machine_configurations = null;

    var add_annoying_reloads = true;
    
    function page_refresh()
    {
        if (add_annoying_reloads)
        {
            location.reload(true);
        }
    }

    function get_user_info()
    {
       var user_info = """ + user_info + """;
       return user_info; 
    }
    
    function on_load_page()
    {
        var user_info = get_user_info();
        console.log("User role: " +  user_info.role);
        if(user_info.role != "user")
        {
            $('#officer_only').show();
            $('#officer_only2').show();
            create_constellation_launcher_widget("launcher_div");
            
        }
        
        create_constellations_widget("constellations_div");
        
        setTimeout(constellation_update , 500);        
    }
    
    
    function constellation_update()
    {
        try
        {
            console.log("update");
            var callback = function(data)
            {
               var constellations = null;
               try
                {
                    
                    constellations = data;
                    remove_old_constellations(constellations);
                    for (var i=0; i< constellations.length; i++)
                    {
                       
                       var constellation = constellations[i];
                       
                       $.publish("/constellation" , constellation);
                      
                    }
                }
                catch(err)
                {
                    // the user is probably logged out.
                    console.log(err.message);
                }
                
               // let's do it again in 500 ms
               setTimeout(constellation_update , 500);
            };
        }
        catch(err)
        {
            console.log("update error: " + err.messagae);
        }
        // lets do it when we get the constellations data
        async_get_constellations(callback);
    }
    </script>
    
    
</head>
<body onload = "on_load_page()">

    <div style="float:left;">
        <!-- img src="/js/images/osrf.png" width="200px"/ -->
        <img src="/js/images/CloudSim_Logo.png" width="200px"/>
        <div  id="server_monitor_div" style="float:left">
        
        <!-- img src="/js/images/DARPA_Logo.jpg" width="200px"/ -->
        <!-- HOLA -->
        
    </div>

<div style="float:right;">

Welcome, """ + role + " " + email + """<br> 
    <div id="officer_only" style="display:none; padding:  0px 0px 0px 0px;" align="right">
    <a href="/cloudsim/inside/cgi-bin/settings">Settings</a><br>
    </div>
    <div style="padding:0px 0px 0px;" align="right">
    <a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
    </div>

 
</div>    


<div style="width:100%; float:left;"><br><hr><br></div>

    <div id='officer_only2' style="display: none;">
    <div id="launcher_div" style="width:100%; float:left; border-radius: 15px; border: 1px solid black; padding: 10px; margin-bottom:20px;  background-color:#f1f1f2;">
    </div>
    </div>
    
    <div id="constellations_div" style="width:100%; float:left; border-radius: 15px;  border: 1px solid black; padding: 10px; margin-bottom:20px; background-color:#f1f1f2;">
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