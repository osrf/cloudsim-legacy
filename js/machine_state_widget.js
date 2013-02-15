
function create_machine_state_widget(machine_div, constellation_name, machine_name, widget_name, key)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);

    // default behaviour
    _update_machine_state(widget_div, "gray", "[waiting for update]");
    
    
    var blink = 0;
    // reaction
    $.subscribe("/constellation", function(event, msg)
    {
    	if(msg.type != 'machine') 
        	return;
        
        if(msg.constellation_name != constellation_name) 
        	return;
        
    	if(msg.machine_name != machine_name) 
        	return;
        
        var machine_state = msg.data.state;
        var color = "red";
        
        if(machine_state == 'shutting-down')
        {
            color = "orange";
        }
        
        if(machine_state == 'pending')
        {
        	color = "yellow";
        }
        	
        if(machine_state == 'terminated')
        {
            color = "red";
        }
        
        if(machine_state == 'running')
        {
            color = "blue";
        }
        
        _update_machine_state(widget_div, color, machine_state);
        
    });
}

function _update_machine_state(widget_div, color, text)
{
    var str = ""; // widget_name;
    var status = status_img(color);
    str += status;
    str += "<b>Machine state:</b> " 
    str += text;
    widget_div.innerHTML = str;
    
}