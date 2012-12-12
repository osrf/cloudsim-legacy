

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
        
        if(data.launch_state == "running")
        {
        	widget_div.innerHTML = "setup complete";
        	return;
        }
        
        if (data.type == "cloud")
        {
            if(data.state != "running")
            {
                widget_div.innerHTML = "";
            }
            return;
        }
        
        if(data.type != 'launch')
        	return;
       /* 
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
       */
	
       var goal = data.goal;
       var colors = ["yellow", "orange", "green"];
       count ++;
       if(count >= colors.length)
       {
           count =0;
       }
       var color = colors[count];
       widget_div.innerHTML = "setup " + status_img(color) + " " + goal;

    });
}
