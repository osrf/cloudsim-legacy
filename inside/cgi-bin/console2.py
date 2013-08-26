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
                    throw err;
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

<table width='100%'>
    <tr>
        <td align='left'>
            <img src="/js/images/CloudSim_Logo.png" width="200px"/>
            <div  id="server_monitor_div">
        </td>
        <td align='right'>
            <span id="head_span">Welcome, """ + role + " " + email + """</span><br>
            <div id="officer_only" style="display:none; padding:  0px 0px 0px 0px;" >
                <a href="/cloudsim/inside/cgi-bin/settings">Settings</a><br>
            </div>
            <div style="padding:0px 0px 0px;" align="right">
                <a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
            </div>
        </td>
    </tr>
</table>



<!-- Add a little space and line -->
<div><br><hr><br></div>

    <!-- Constellation provisioning widget -->
    <div id='officer_only2' style="display: none;">
        <div id="launcher_div" ></div>
    </div>

    <!-- Constellation view widget -->
    <div id="constellations_div"></div>


<!-- Add a little space and a line -->
<div><br><hr></div>


<!-- Footer -->

<table width='100%'>
    <tr>
        <td align='left'>
           CloudSim Version <b>""" + version + """</b>
        </td>
        <td align='right'>
           <img src="/js/images/osrf-pos-horz-cmyk.png" height="30px"/> 
        </td>
    </tr>
</table>



</body>
</html>

"""

print(page)