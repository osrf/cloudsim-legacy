

function create_simulator_state_widget(machine_div, constellation_name, machine_name, glx_key, simulator_key )
{
    var widget_div = _create_empty_widget(machine_div, "simulator");
    var status = status_img("gray");
    widget_div.innerHTML = status + "<b>Simulator</b>";
    
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        var color = "gray";
        var simulator_running = false;
        
        // X and simulator must be running
        if (data[glx_key] == "running")
        {
            if(data[simulator_key] == "running")
            {
            	simulator_running = true;
            }
        }
        else
        {
        	color = 'red';
        }

        if(color == 'red' )
        {
            widget_div.querySelector("img").src = "/js/images/red_status.png";
        }
        else
        { 	
	        if(simulator_running )
	        {
	            widget_div.querySelector("img").src = "/js/images/blue_status.png";
	        }
	        else
	        {
	            widget_div.querySelector("img").src = "/js/images/gray_status.png";
	        }
        }
    });
}


