#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    get_cloudsim_version_txt, print_http_header, get_meta, get_frame
cgitb.enable()


email = authorize("admin")
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)



version = get_cloudsim_version_txt()

user = {'user':email, 'role':'admin'}

user_info = json.dumps(user)
scripts = get_javascripts(['jquery-1.8.3.min.js'])

print_http_header()
meta = get_meta()
frame = get_frame(email, 'Settings')

page =  """<!DOCTYPE html>
<html lang="en">
<head>
    """ + meta + """
    <title>CloudSim - Settings</title>
    """ + scripts +"""
    
<script language="javascript">
    $(function(){
        $('.admin_only').show();
        
        add_osrf_cloud_credentials_widget("osrf_credentials_div");
        add_cloud_credentials_widget("amazon_credentials_div");
        add_users_admin_widget("users_div");
        
        setTimeout(users_update , 500);
    });
    
    function users_update()
    {
        try
        {
            var callback = function(str_data)
            {
                var users = eval( '(' + str_data + ')' );
                $.publish('/users',users);
                setTimeout(users_update , 500);
            };
        }
        catch(err)
        {
            console.log("update error: " + err.messagae);
        }
        async_get_users(callback);
    }    
</script>
    

</head>
<body onload = "on_load_page()">""" + frame + """
    <section id="main" class="column admin_only" style="display:none;">
        <article class="module width_3_quarter">
            <header><h3>OSRF Cloud Credentials</h3></header>
            <div class="module_content">
                <div id="osrf_credentials_div"></div>
            </div>
        </article>
        <article class="module width_quarter">
                <div class="module_content" style="text-align:center;">
                <p style="text-align:left;">Download the CloudSim SSH key below for sftp access.</p>
                    <a href="/cloudsim/inside/cgi-bin/admin_download">
                    <button type="button" style="background: #3573c0; color: white; font: bold 14px; padding: 4px; cursor: pointer; -moz-border-radius: 4px; -webkit-border-radius: 4px;">Download SSH Key</button></a>
                </div>
        </article>
        <article class="module width_3_quarter">
            <header><h3>Amazon Web Services Credentials</h3></header>
            <div class="module_content">
                <div id="amazon_credentials_div"></div>
            </div>
        </article>
        <article class="module width_3_quarter">
            <header><h3>CloudSim Users</h3></header>           
            <div id="users_div"></div>
        </article>
        
        
        <div class="clear"></div>
        <div class="spacer"></div>
    </section>   
</body>
</html>
"""

print(page)