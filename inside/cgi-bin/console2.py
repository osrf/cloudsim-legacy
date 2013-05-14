#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import os

from common.web import get_javascripts, authorize, UserDatabase,\
    print_http_header, get_meta, get_frame
cgitb.enable()


email = authorize()
method = os.environ['REQUEST_METHOD']


if method != 'GET':
    exit(0)

email = authorize()
udb = UserDatabase()
role = udb.get_role(email)
meta = get_meta()
frame = get_frame(email, 'Console')

user_info = json.dumps({'user':email, 'role':role})
scripts = get_javascripts(['jquery-1.8.3.min.js', 'jquery.flot.js' ])

print_http_header()

page =  """<!DOCTYPE html>
<html lang="en">
<head>
    <title>CloudSim - Console</title>""" + meta + """
    <script language="javascript">
    $(function(){
        var user_info = get_user_info();
        console.log("User role: " +  user_info.role);
        if(user_info.role != "user")
        {
            $('.officer_only').show();
            create_constellation_launcher_widget("launcher_div");
        }
        create_constellations_widget("constellations_div");
        setTimeout(constellation_update , 500); 
    });
    function get_user_info()
    {
       var user_info = """ + user_info + """;
       return user_info; 
    }
    
    function constellation_update()
    {
        try
        {
            console.log("update");
            var callback = function(str_data)
            {
               var constellations = eval( '(' + str_data + ')' );
               for (var i=0; i< constellations.length; i++)
               {
                   var constellation = constellations[i];
                   $.publish("/constellation" , constellation);
               } 
               // that was fun, let's do it again in 500 ms
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
<body>""" + frame + """
    <section id="main" class="column">
        <article class="module width_full officer_only" style="display:none;">
            <header><h3>Launch a Machine Constellation</h3></header>
            <div id="launcher_div"></div>
        </article>
        <article class="module width_full">
            <header><h3>Constellations</h3></header>
            <div class="module_content" style="overflow:hidden;">
                <div id="constellations_div"></div>
            </div>
        </article>
        <div class="clear"></div>
        <div class="spacer"></div>
    </section>    
</body>
<script language="javascript" type="text/javascript" src="/cloudsim/js/jquery/jquery.flot.js"></script>
""" + scripts +"""
</html>

"""

print(page)