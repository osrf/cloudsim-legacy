
function create_machine_state_widget(machine_div, constellation_name, machine_name, widget_name)
{

    
    var widget_div = _create_empty_widget(machine_div, widget_name);

    // default behaviour
    _update_machine_state(widget_div, "gray", "[waiting for update]");
    
    // reaction
    $.subscribe("/cloudsim", function(event, data){
        if(data.type == 'cloud')
        {
            var color = "red";
            if(data.result == 'success')
            	color = "blue";
            _update_machine_state(widget_div, color, data.state);
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