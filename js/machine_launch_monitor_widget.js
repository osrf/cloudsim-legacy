

function create_machine_launch_monitor_widget(machine_div, 
                                              constellation_name, 
                                              machine_name,  
                                              widget_name,
                                              key)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);
    
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
        widget_div.innerHTML =  status_img(data.color) + error_txt +  "<b>Launch:</b>  " + data.text;
        
    });
}
