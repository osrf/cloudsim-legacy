

function create_machine_launch_monitor_widget(machine_div, constellation_name, machine_name,  widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);
    
    var status = status_img("gray");
    
    widget_div.innerHTML = status;
        
    var count = 0;
    
    $.subscribe("/cloudsim", function(event, data){
        
        if(data.constellation_name != constellation_name)
            return;
        
        if(data.machine_name != machine_name)
            return;
        
        if(data.type != 'launch')
        	return;

       	widget_div.innerHTML =  status_img(data.color) + "<b>Launch:</b>  " + data.text;
        
    });
}
