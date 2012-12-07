

function create_simulator_state_widget(machine_div, constellation_name, machine_name,  widget_name)
{
    var package_name = "drc_robot_utils";
    var launch_file = "drc_robot.launch";
    var launch_args = "";
	
    var widget_div = _create_empty_widget(machine_div, widget_name);
    
    var status = status_img("gray");
    widget_div.innerHTML = status;
    
    var package_text = document.createElement('input');
    package_text.setAttribute('type','text');
    package_text.setAttribute('name','pack');
    package_text.setAttribute('value', package_name);
    
    var launch_file_text = document.createElement('input');
    launch_file_text.setAttribute('type','text');
    launch_file_text.setAttribute('name','launch');
    launch_file_text.setAttribute('value',launch_file);   
    
    var args_text = document.createElement('input');
    args_text.setAttribute('type','text');
    args_text.setAttribute('name','args');
    args_text.setAttribute('value',launch_args);
    
    var start_button= document.createElement('input');
    start_button.setAttribute('type','button');
    start_button.setAttribute('name','start');
    start_button.setAttribute('value','Start');
    
	start_button.onclick =  function()
    {   
        var package_name = package_text.value;
        var launch_file = launch_file_text.value;
        var launch_args = args_text.value;
        _start_simulator(constellation_name, machine_name, package_name, launch_file, launch_args)

    };
    
    
    var stop_button= document.createElement('input');
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('name','stop');
    stop_button.setAttribute('value','Stop');

    stop_button.onclick =  function(){
        _stop_simulator(constellation_name, machine_name);
    };
    
    widget_div.appendChild(document.createTextNode("package: "));
    widget_div.appendChild(package_text);
    widget_div.appendChild(document.createTextNode("launch file: "));
    widget_div.appendChild(launch_file_text);
    widget_div.appendChild(document.createTextNode("args: "));
    widget_div.appendChild(args_text);
    
    widget_div.appendChild(start_button);
    widget_div.appendChild(stop_button);
    

    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        if(data.machine_name != machine_name)
            return
            
        if(data.type == 'simulator')
        {
            
            var color = "red";
            if(data.result == 'success')
            {
                
            	widget_div.querySelector("img").src = "/js/images/blue_status.png";
            }
            else
            {
                widget_div.querySelector("img").src = "/js/images/red_status.png";
            }
        }
        
    });
}

function _update_glx_state(widget_div, color, text)
{
    var status = status_img(color);
    var str = "X and GL state: "
    str += status;
    str += text;
    widget_div.innerHTML = str;
    
}

function create_glx_state_widget(machine_div, constellation_name, machine_name,  widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);

    // default behaviour
    _update_glx_state(widget_div, "gray", "[waiting for update]");
    
    // reaction
    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        if(data.machine_name != machine_name)
            return
            
        if(data.type == 'graphics')
        {
        	var text = "test failed";
            var color = "red";
		    if(data.result == 'success')
		    {
		        color = "blue";
		        text = "running";	
		    }
		    
		    _update_glx_state(widget_div, color, text);
        }
        
    });
}



function _start_simulator(constellation_name, machine_name, package_name, launch_file_name, launch_args)
{

    var r=confirm("Start simulator on machine " + machine_name + "?");
    if (r==false)
    {
        return;
    }    
    start_simulator(constellation_name, machine_name, package_name, launch_file_name, launch_args)


}



function _stop_simulator(constellation_name, machine_name)
{
    var r=confirm("Stop simulator on machine " + machine_name + "?");
    if (r==false)
    {
        return;
    }    
    stop_simulator(constellation_name, machine_name);

}
