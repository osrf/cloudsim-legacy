
function create_hostname_widget(machine_div, 
                                constellation_name, 
                                machine_name,  
                                key_ip, 
                                key_aws_id, 
                                key_user, 
                                key_launch_date, 
                                key_is_download_ready)
{
    
    var widget_div = _create_empty_widget(machine_div, "hostname");
    _update_hostname_widget(widget_div, constellation_name, machine_name, "xxx.xxx.xxx", "x-xxxxx", "xx@xx.xxx", "xxxx-xx-xx xx:xx:xx");
    
    $.subscribe("/cloudsim", function(event, msg){
        if(msg.constellation_name != constellation_name)
            return;
        if(msg.machine_name != machine_name)
            return
            
        if(msg.type == 'machine')
        {
            var data = msg.data;
            _update_hostname_widget(widget_div, constellation_name, machine_name, 
            data.ip, data.aws_id, data.username, data.gmt, data.key_download_ready );
        }
    });
    
    $.subscribe("/constellation", function(event, msg){
        if(msg.constellation_name != constellation_name)
            return;
        
        _update_hostname_widget(widget_div, 
                                constellation_name, 
                                machine_name, 
                                msg[key_ip], 
                                msg[key_aws_id], 
                                msg[key_user], 
                                msg[key_launch_date], 
                                msg[key_is_download_ready]);
       
    });
    
}


function _update_hostname_widget(widget_div, 
                                 constellation_name, 
                                 machine_name, 
                                 ip, 
                                 aws_id, 
                                 user, 
                                 launch_date, 
                                 is_download_ready)
{
		
    var str = "";
    str += "<b>IP</b> " + ip + " ("
    str += "<b>AWS id</b> " + aws_id +") ";
    
    if(is_download_ready)
    {
        str += '<a href="/cloudsim/inside/cgi-bin/machine_zip_download.py';
        str += '?constellation=' + constellation_name;
        str += '&machine=' + machine_name;
        str += '">Download keys</a>';
	}
    str += '<br>';
    str += '<b>Launched by: </b>' + user + " ( at GMT " + launch_date+ ")";
    widget_div.innerHTML = str;
}




