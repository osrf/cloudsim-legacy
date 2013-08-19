#!/usr/bin/env python
from __future__ import with_statement
from __future__ import print_function

import cgitb
import json
from common import get_javascripts
cgitb.enable()

import common
from common import  authorize


email = authorize()
udb = common.UserDatabase()
role = udb.get_role(email)
user_info = json.dumps({'user':email, 'role':role})

scripts = get_javascripts([ 'jquery.flot.js' ])

print("Content-Type: text/html")
print("\n")


# <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN" "http://www.w3.org/TR/html4/loose.dtd">


#    <script language="javascript" type="text/javascript" src="/js/jquery-1.8.3.min.js"></script>
#    <script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>
#    



template = """ 
<!DOCTYPE html>
<html>
 <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8">
    <title>CloudSim seeder</title>
    
<link href="/js/layout.css" rel="stylesheet" type="text/css">
<link rel="stylesheet" href="/js/jquery-ui.css" />

<script src="//ajax.googleapis.com/ajax/libs/jquery/1.8.3/jquery.min.js"></script>
<script src="//ajax.googleapis.com/ajax/libs/jqueryui/1.9.2/jquery-ui.min.js"></script>


<script language="javascript" type="text/javascript" src="/js/jquery.flot.js"></script>
    
""" + scripts +"""
    

<script language="javascript">

    /////////////////////////////////////////////
    
    // "You Can Recognize A Pioneer By The Arrows In His Back."
    
    
    function cloudseed(email, key, secret )
    {
        alert('user: ' +email + " key: '"+  key + "'  secret: '" + secret + "'");
        
        var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=cloudseed'; 
        url += '&email=' + email;
        url += '&key=' + key;
        url += '&secret=' + secret;
        
        console.log(url);
        msg = httpGet(url);
        console.log(msg);    
        
    }
    
    function create_cloudseed_widget(div_name)
    {
        var div = document.getElementById(div_name);
        
        var username_text = document.createElement('input');
        username_text.setAttribute('type','text');
        
        var key_text = document.createElement('input');
        key_text.setAttribute('type','text');
        
        var secret_text = document.createElement('input');
        secret_text.setAttribute('type','text');
        
        var launch_button= document.createElement('input');
        launch_button.setAttribute('type','button');
        launch_button.setAttribute('value','Launch');
    
        launch_button.onclick =  function()
        {   
            var x = confirm("Are you sure?");
            if(!x) return;
            
            var email = username_text.value;
            var key = key_text.value;
            var secret = secret_text.value;
            
            cloudseed(email, key, secret);
            
        };
        
        
        
        var status_img = document.createElement('img');
        status_img.src = "/js/images/gray_status.png";
        
        
        div.appendChild(document.createTextNode("email: "));
        div.appendChild(username_text);
        
        div.appendChild(document.createTextNode("AWS key: "));
        div.appendChild(key_text);
        
        div.appendChild(document.createTextNode("AWS secret key: "));
        div.appendChild(secret_text);
        
        div.appendChild(launch_button);
        
        var div = document.getElementById("prog_div");
        $( "#"+ div_name ).progressbar({
            value: 37
        });
        var progress = 0;
        var test_button= document.createElement('input');
        test_button.setAttribute('type','button');
        test_button.setAttribute('value','Test');
        test_button.onclick =  function()
        {
            
            progress += 10;
            
        }
        div.appendChild(test_button);
    }
    
    
    ////////////////////////////////////////////

    function create_progress_widget(div_name)
    {
         var div = document.getElementById(div_name);
        $( "#"+ div_name ).progressbar({
            value: 37
        });
    }
    
    ////////////////////////////////////////////   

    function on_load_page()
    {
        var user_info = """ + user_info + """;
        if(user_info.role == "admin")
        {
            $('.admin_only').show();
        }
        
        // create_progress_widget("prog_div");
        
        create_server_monitor_widget("server_monitor_div");
        create_cloudseed_widget("cloudseed_div");
        
        
        
        stream();
    }
    
    var log_events = true;
    
    function stream()
    {
        
        var stream_url = '/cloudsim/inside/cgi-bin/console_stream.py';
        console.log(stream_url);
        
        var es = new EventSource(stream_url);
        
        
        es.addEventListener("cloudsim", function(event)
        {
             var str_data = event.data;
             if(log_events)
                 console.log(str_data);
             var data = eval( '(' + str_data + ')' );
             $.publish("/cloudsim", data);
             
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
    
    
    <h1>CloudSeed</h1>
    <div id="server_monitor_div"></div>
    <div id="cloudseed_div"></div>
    
     
    
    <div id="prog_div"></div>

<br>
<hr>
    <div style="float:right;">
        <img src="/js/images/osrf.png" width="200px"/>
        
    </div>

<div style="float:left;">

Logged in as: """ + email + """<br>
<a href="/cloudsim/inside/cgi-bin/logout">Logout</a><br>
<div class="admin_only" style="display:none;">
    <a href="/cloudsim/inside/cgi-bin/admin_download">SSH key download</a><br>
</div>
</div>    
    
</body>
</html>

"""

page = template 
print(page )
