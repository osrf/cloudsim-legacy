function get_configurations()
{
	var url = "/cloudsim/inside/cgi-bin/machine_configs";
	console.log("[GET]" + url);
	var x = httpGet(url);
    var machine_configurations = eval( '(' + x + ')' );
    return machine_configurations;
}

function launch_constellation(cloud_provider, configuration)
{

    var p = encodeURIComponent(cloud_provider);
    var c = encodeURIComponent(configuration);
    var url = '/cloudsim/inside/cgi-bin/constellations?cloud_provider=' + p + '&configuration=' + c;

    console.log("[POST]" + url);
    msg = httpPost(url);
    console.log(msg);
}


function update_constellation(constellation_name)
{
	var url = '/cloudsim/inside/cgi-bin/constellations';
    url += '/' + constellation_name;

    console.log("[PUT (update)]" + url);
    msg = httpPut(url);
    console.log(msg);
    return msg;
}

function terminate_constellation(constellation_name)
{
    var url = '/cloudsim/inside/cgi-bin/constellations';
    url += '/' + constellation_name;

    console.log("[DELETE] " + url);
    msg = httpDelete(url);
    console.log( msg);
}

function get_users()
{
	var url = '/cloudsim/inside/cgi-bin/users/';
	console.log("[GET]" + url);
	var x = httpGet(url);
    var r = eval( '(' + x + ')' );
    return r;
}

function add_user(user_name, role, password)
{
    var url = "/cloudsim/inside/cgi-bin/user?user=" + user_name;
    url +="&role=" + role;
    if(password)
    url += "&passwd=" + password;
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
    return x;
}

function set_portal_info(phostname, pteam)
{
	var hostname = encodeURIComponent(phostname);
	var team = encodeURIComponent(pteam);
	var url = '/cloudsim/inside/cgi-bin/portal';
	url += '?hostname=' + hostname;
    url += '&team=' +team;
    console.log("[PUT] " + url);
    var msg = httpPut(url);
    var jmsg = eval('(' + msg + ')');
    console.log("set_portal_info: " + msg);
    return jmsg;
}

function get_portal_info()
{
    var url = '/cloudsim/inside/cgi-bin/portal';
    console.log("[GET] " + url);
    var msg = httpGet(url);
    var jmsg = eval('(' + msg + ')');
    console.log("get_portal_info: " + msg);
    return jmsg;
}

function change_osrf_credentials(nuser, napi_key)
{
    var user = encodeURIComponent(nuser);
    var api_key = encodeURIComponent(napi_key);
    var url = '/cloudsim/inside/cgi-bin/cloud_credentials_softlayer?user=';
    url += user+'&api_key=' +api_key;
    console.log("[PUT] " + url);
    var msg = httpPut(url);

    var jmsg = eval('(' + msg + ')');
    console.log("change_credentials: " + msg);
    return jmsg;
}

function change_aws_credentials(access_key, secret_access_key, availability_zone)
{
    var key = encodeURIComponent(access_key);
    var secret = encodeURIComponent(secret_access_key);
    var url = '/cloudsim/inside/cgi-bin/cloud_credentials?access_key=';
    url += key+'&secret_access_key=' + secret;
    url += "&availability_zone="+availability_zone;
    console.log("[PUT] " + url);
    var msg = httpPut(url);

    var jmsg = eval('(' + msg + ')');
    console.log("change_credentials: " + msg);
    return jmsg;
}


function start_simulator(constellation_name, machine_name, package_name, launch_file_name, launch_args)
{
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=start_simulator';
    url += '&constellation=' + constellation_name;
    url += '&machine=' + machine_name;
    url += '&package=' + package_name;
    url += '&launch_file_name=' + launch_file_name;

    if(launch_args)
    {
        url += '&launch_args=' +  launch_args;
    }

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function stop_simulator(constellation_name, machine_name)
{

    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=stop_simulator';
    url += '&constellation=' + constellation_name;
    url += '&machine=' + machine_name;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function update_traffic_shaper(_constellationName, _machineName, _targetPacketLatency)
{
    var url = '/cloudsim/inside/cgi-bin/tc_cmd.py?command=update_tc';
    url += '&constellation=' + _constellationName;
    url += '&machine=' + _machineName;
    url += '&targetPacketLatency=' + _targetPacketLatency;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function get_constellations()
{
    var url = '/cloudsim/inside/cgi-bin/constellations';
    // console.log(url);
    var msg = httpGet(url);
    // console.log(msg);
    var jmsg = eval('(' + msg + ')');
    return jmsg;
}

function get_constellation(constellation)
{
    var url = '/cloudsim/inside/cgi-bin/constellations/';
    url += constellation;
    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function _get_task_url(constellation,
                        task_id,
                        task_title,
                        ros_package,
                        launch_file,
                        timeout,
                        launch_args,
                        latency,
                        uplink_data_cap,
                        downlink_data_cap,
                        local_start,
                        local_stop,
                        vrc_id,
                        vrc_num)
{
    console.log("task_id " + task_id)
    console.log("task_title " + task_title)
    console.log("ros_package " + ros_package)
    console.log("ros_launch " + launch_file)
    console.log("launch_args " + launch_args)
    console.log("timeout " + timeout)
    console.log("latency " + latency)
    console.log("uplink_data_cap " + uplink_data_cap)
    console.log("downllink_data_cap " + downlink_data_cap)
    console.log("local_start " + local_start)
    console.log("local_stop " + local_stop)
    console.log("vrc_id " + vrc_id)
    console.log("vrc_num " + vrc_num)

    var url = '/cloudsim/inside/cgi-bin/tasks/' + constellation + "?";

    if(task_id)
        url += 'task_id=' + encodeURIComponent(task_id);
        url += '&'
    if(task_title != "")
        url += 'task_title=' + encodeURIComponent(task_title);
    if(ros_package != "")
        url += '&ros_package=' + encodeURIComponent(ros_package);
    if(launch_file != "")
        url += '&ros_launch=' + encodeURIComponent(launch_file);
    if(launch_args != "")
    	url += '&ros_args=' + encodeURIComponent(launch_args);
    if(timeout != "")
    	url += '&timeout=' + encodeURIComponent(timeout);
    if(latency != "")
        url += '&latency=' + encodeURIComponent(latency);
    if(uplink_data_cap != "")
        url += '&uplink_data_cap=' + encodeURIComponent(uplink_data_cap);
    if(downlink_data_cap != "")
        url += '&downlink_data_cap=' + encodeURIComponent(downlink_data_cap);
    if( local_start != "")
        url += '&local_start=' + encodeURIComponent(local_start);
    if( local_stop != "")
        url += '&local_stop=' + encodeURIComponent(local_stop);
    if( vrc_id != "")
        url += '&vrc_id=' + encodeURIComponent(vrc_id);
    if( vrc_num != "")
        url += '&vrc_num=' + encodeURIComponent(vrc_num);

    return url;
}

function create_task(constellation,
					task_title,
                  ros_package,
                  launch_file,
                  timeout,
                  launch_args,
                  latency,
                  uplink_data_cap,
                  downlink_data_cap,
                  local_start,
                  local_stop,
                  vrc_id,
                  vrc_num)
{


    var url = _get_task_url(constellation,
    			  null,
    			  task_title,
                  ros_package,
                  launch_file,
                  timeout,
                  launch_args,
                  latency,
                  uplink_data_cap,
                  downlink_data_cap,
                  local_start,
                  local_stop,
                  vrc_id,
                  vrc_num)

    console.log("[POST (create)]" + url);
    msg = httpPost(url);
    console.log(msg);
    return msg;
}

function read_task(constellation, task_id)
{
    var url = '/cloudsim/inside/cgi-bin/tasks/' + constellation + '/' + task_id;
    console.log("[GET] "+ url);
    msg = httpGet(url);
    console.log(msg);
    var jmsg = eval('(' + msg + ')');
    return jmsg;
}

function update_task(constellation,
                     task_id,
                     task_title,
                    ros_package,
                    launch_file,
                    timeout,
                    launch_args,
                    latency,
                    uplink_data_cap,
                    downlink_data_cap,
                    local_start,
                    local_stop,
                    vrc_id,
                    vrc_num)
{

    var url = _get_task_url(constellation,
                  task_id,
                  task_title,
                  ros_package,
                  launch_file,
                  timeout,
                  launch_args,
                  latency,
                  uplink_data_cap,
                  downlink_data_cap,
                  local_start,
                  local_stop,
                  vrc_id,
                  vrc_num)


    console.log("[PUT (update)]" + url);
    msg = httpPut(url);
    console.log(msg);
    return msg;
}

function delete_task(constellation, task_id)
{
    var url = '/cloudsim/inside/cgi-bin/tasks/' + constellation + '/' + task_id;
    console.log("[DELETE] "+ url);
    msg = httpDelete(url);
    console.log(msg);
    return msg;
}

function start_task(constellation_name, task_id)
{
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=start_task';
    url += '&constellation=' + constellation_name;
    url += '&task_id=' +task_id

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function stop_task(constellation_name)
{
	stop_web_tools(constellation_name);
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=stop_task';
    url += '&constellation=' + constellation_name;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function reset_tasks(constellation_name)
{
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=reset_tasks';
    url += '&constellation=' + constellation_name;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function start_web_tools(constellation_name)
{
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=start_gzweb';
    url += '&constellation=' + constellation_name;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}

function stop_web_tools(constellation_name)
{
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=stop_gzweb';
    url += '&constellation=' + constellation_name;

    console.log(url);
    msg = httpGet(url);
    console.log(msg);
    return msg;
}


function async_get_constellations(callback)
{
	var url = '/cloudsim/inside/cgi-bin/constellations/';

	$.ajax({
		url: url,
		cache: false,
		success: function(json)
		{
			callback(json);
		}
	});
}

function async_get_constellation(constellation, callback)
{
	var url = '/cloudsim/inside/cgi-bin/constellations/';
	url += constellation;

	$.ajax({
		url: url,
		cache: false,
		success: function(json)
		{
			callback(json);
		}
	});
}

function async_get_users(callback)
{
	var url = '/cloudsim/inside/cgi-bin/users/';
    // console.log(url);
	$.ajax({
		url: url,
		cache: false,
		success: function(json)
		{
			callback(json);
		}
	});
}

////////////////////////////////////////

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
