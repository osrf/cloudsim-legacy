

function _update_hostname_widget(widget_div, constellation_name, machine_name, ip, aws_id, user, launch_date, is_download_ready)
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

function create_hostname_widget(machine_div, constellation_name, machine_name, widget_name)
{
    
    var widget_div = _create_empty_widget(machine_div, widget_name);
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
    
}






