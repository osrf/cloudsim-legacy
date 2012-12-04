

function _update_hostname_widget(widget_div, constellation_name, machine_name, ip, aws_id, user)
{
		
    var str = "";
    str += "<b>IP</b> " + ip + " ("
    str += "<b>AWS id</b> " + aws_id +") ";
    str += '<a href="/cloudsim/inside/cgi-bin/machine_zip_download.py';
    str += '?constellation=' + constellation_name;
    str += '&machine=' + machine_name;
    str += '">Download keys</a><br>';
    str += '<b>Launched by: </b>' + user;
    widget_div.innerHTML = str;
}

function create_hostname_widget(machine_div, constellation_name, machine_name, widget_name)
{
    
    var widget_div = _create_empty_widget(machine_div, widget_name);
    _update_hostname_widget(widget_div, constellation_name, machine_name, "xxx.xxx.xxx", "x-xxxxx");
    
    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        if(data.machine_name != machine_name)
            return
            
        if(data.type == 'cloud')
        {
        	_update_hostname_widget(widget_div, constellation_name, machine_name, 
        		data.ip, data.aws_id, data.user);
        }
        
        
    });
    
}






