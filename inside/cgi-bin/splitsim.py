#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os
import urlparse

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header
cgitb.enable()

def get_query_param(param, default=""):
    qs = os.environ['QUERY_STRING']
    params = urlparse.parse_qs(qs)
    p = None
    try:
        p = params[param][0]
    except:
        p = default
    return p

email = authorize()
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)
version = get_cloudsim_version_txt()

user_info = json.dumps({'user': email, 'role': role})

sim_ip = get_query_param("sim_ip")
notebook_id = get_query_param("notebook_id")

scripts = ""
#scripts = get_javascripts(['jquery-1.8.3.min.js', 'jquery.flot.js' ])


print_http_header()

#page =  """<!DOCTYPE html>

page = """
<html>
 <head>

    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>Cloudsim split simulation view</title>


<!--
<link href="/js/layout.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/js/jquery-ui.css" />
<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.10.1/jquery-ui.min.js"></script>
<script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>

-->

""" + scripts + """


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
        if(user_info.role == "admin")
        {
            $('#admin_only1').show();

        }
    }

</script>

</head>
<body onload = "on_load_page()">

<!-- Header -->

<table width='100%'>
    <tr>
        <td align='left'>
            <img src="/js/images/CloudSim_Logo.png" width="200px"/>
            <div  id="server_monitor_div">
        </td>
        <td align='right'>
            <span id="head_span">Welcome, """ + role + " " + email + """</span><br>
            <div id="admin_only1" style="display:none; padding:  0px 0px 0px 0px;" >
                <a href="/cloudsim/inside/cgi-bin/settings">Settings</a><br>
            </div>
            <div style="padding:0px 0px 0px;" align="right">
                <a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
            </div>
        </td>
    </tr>
</table>

<div><br><hr><br></div>


<center>
<iframe name="gzweb_frame" src=http://""" + sim_ip + """:8080 width="49%" height="80%"></iframe>
<iframe name="ipynb_frame" src=http://""" + sim_ip + ":8888/" + notebook_id + """ width="49%" height="80%"></iframe>
</center>



<!-- Add a little space and a line -->
<div><br><hr></div>



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