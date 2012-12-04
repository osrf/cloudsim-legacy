
function launch_constelaltion(configuration)
{
    var url = '/cloudsim/inside/cgi-bin/constellation?configuration=' + configuration;
    
    console.log("[POST]" + url);
    msg = httpPost(url);
    console.log(msg);
}

function terminate_constellation(constellation_name)
{
    var url = '/cloudsim/inside/cgi-bin/constellation';
    url += '/' + constellation_name;
        
    console.log("[DELETE] " + url);
    msg = httpDelete(url);
    console.log( msg);
}


function add_user(user_name, role)
{
    var url = "/cloudsim/inside/cgi-bin/user?user=" + user_name;
    url +="&role=" + role;
    console.log("[POST] " + url);
    var x = httpPost(url);
    console.log(x);
	
}

function remove_user(user_name)
{
    var url = "/cloudsim/inside/cgi-bin/user?user=" + user_name;
    console.log("[DELETE] "+url);
    var x = httpDelete(url);
    console.log(x);
}

function change_credentials(access_key, secret_access_key)
{
    var key = encodeURIComponent(access_key);
    var secret = encodeURIComponent(secret_access_key);
    var url = '/cloudsim/inside/cgi-bin/cloud_credentials?access_key=';
    url += key+'&secret_access_key=' + secret;
    console.log("[PUT] " + url);
    var msg = httpPut(url);
    
    var jmsg = eval('(' + msg + ')');
    console.log("change_credentials: " + msg);
    alert(jmsg['msg']);
}

///////////////////////// AJAX

function httpGet(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function httpPut(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "PUT", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function httpPost(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "POST", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function httpDelete(theUrl)
{
    var xmlHttp = null;

    xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "DELETE", theUrl, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function log_to_div(div_name, message)
{
   document.getElementById(div_name).innerHTML += message +"<br>"; 
}

function clear_div(div_name)
{
   document.getElementById(div_name).innerHTML = "";  
}

///////////////// pub sub 


/* jQuery Tiny Pub/Sub - v0.7 - 10/27/2011
 * http://benalman.com/
 * Copyright (c) 2011 "Cowboy" Ben Alman; Licensed MIT, GPL */

(function($) {

  var o = $({});

  $.subscribe = function() {
    o.on.apply(o, arguments);
  };

  $.unsubscribe = function() {
    o.off.apply(o, arguments);
  };

  $.publish = function() {
    o.trigger.apply(o, arguments);
  };

}(jQuery));
