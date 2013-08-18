
function create_machine_state_widget(machine_div, constellation_name, machine_name, key)
{
    var widget_div = _create_empty_widget(machine_div, "state");
    // default behaviour
    _update_machine_state(widget_div, "gray", "[waiting for update]");
    
    var current_color = "";
    var current_text = "";
    // reaction
    $.subscribe("/constellation", function(event, msg)
    {
        
        if(msg.constellation_name != constellation_name) 
            return;
        
        var machine_state = msg[key];
        var color = "red";
        
        if(machine_state == 'shutting-down')
        {
            color = "orange";
        }
        
        if(machine_state == 'nothing')
        {
            color = "yellow";
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
        if( (current_color != color)  || (current_text != machine_state) )
        {
        	_update_machine_state(widget_div, color, machine_state);
        }
        current_color = color;
        current_text = machine_state;
    });
}

function _update_machine_state(widget_div, color, text)
{
    var str = ""; // widget_name;
    var status = status_img(color);
    str += status;
    str += "<b>Machine state:</b> " 
    str += text;
    if(widget_div.innerHTML != str)
    widget_div.innerHTML = str;
}