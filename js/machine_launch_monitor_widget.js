

function create_machine_launch_monitor_widget(machine_div, 
                                              constellation_name, 
                                              machine_name,  
                                              message_key,
                                              state_key)
{
    var widget_div = _create_empty_widget(machine_div, "launch");
    
    var status = status_img("gray");
    
    widget_div.innerHTML = status;
        
    var count = 0;
    
    $.subscribe("/constellation", function(event, data){
        
        if(data.constellation_name != constellation_name)
            return;
        
        var error_txt = "";
        if ( data.error.length)
        {
        	error_txt += "<font color='red'><b>" +data.error  +"</b></font><br>";	
        }
        var colors = ["yellow", "orange"]
        var color = colors[count % colors.length]
        count ++;
        var machine_state = data[state_key];
        if(machine_state == "running")
            color = "blue";
        if(data[state_key] == "terminated")
            color = "red";
        
        widget_div.innerHTML =  status_img(color) + error_txt +  "<b>Launch:</b>  " + data[message_key];
        
    });
}
