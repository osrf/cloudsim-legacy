

function create_machine_launch_monitor_widget(machine_div, constellation_name, machine_name,  widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);
    
    // var status = status_img("gray");
    
    widget_div.innerHTML = "[no updates]"; // + status;
        
    
    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        if(data.machine_name != machine_name)
            return;
            
        if(data.type != 'launch')
        	return;
        
        	if(data)
		
       var str = "";
       for (var key in data )
       {
           var value = data[key]; 
           if (key != "status" && key != "machine" && key != "hostname" && key != "type" && key != "success")
           {
        	   str += "<b>" + key + "</b>: " + value + "<br>";
           }
       }
       widget_div.innerHTML = str;
    });
}
