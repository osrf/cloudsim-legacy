
function create_machine_state_widget(machine_div, constellation_name, machine_name, widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);

    // default behaviour
    _update_machine_state(widget_div, "gray", "[waiting for update]");
    
    
    var blink = 0;
    // reaction
    $.subscribe("/cloudsim", function(event, data)
    {
        if(data.constellation_name != constellation_name) return;
        if(data.machine_name != machine_name) return;

        if(data.type == 'cloud')
        {
            var color = "red";
            if(data.result != 'success')
            {
            	color = "red";
            	_update_machine_state(widget_div, color, "error");
            	return;
            }
            
            if(data.state == 'shutting-down' && data.result == 'success')
            {
                color = "orange";
                str = 'shutting-down';
                _update_machine_state(widget_div, color, str);
            	return;
            }
            
            if(data.state == 'terminated' && data.result == 'success')
            {
                color = "orange";
                str = 'terminated';
                _update_machine_state(widget_div, color, str);
            	return;
            }
            
            if(data.state == 'running' && data.result == 'success')
            {
                color = "blue";
            }
            
            var str = data.state;
            if(data.launch_state != "running")
            {
            	color = "yellow";
                str = data.launch_state;
            }
            
            _update_machine_state(widget_div, color, str);
        }
        
        
        
    });
}

function _update_machine_state(widget_div, color, text)
{
    var str = "Machine state: "; // widget_name;
    var status = status_img(color);
    str += status;
    str += text;
    widget_div.innerHTML = str;
    
}