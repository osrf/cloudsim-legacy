

function create_simulator_state_widget(machine_div, constellation_name, machine_name, glx_key, simulator_key )
{
	// roslaunch atlas_utils atlas_position_controllers.launch
    var package_name = "atlas_utils";//"drc_robot_utils";
    var launch_file = "atlas.launch"; // "drc_robot.launch";
    var launch_args = "";
	
    var widget_div = _create_empty_widget(machine_div, "simulator");
    
    var status = status_img("gray");
    widget_div.innerHTML = status + "<b>Simulator</b>";
/*    
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
    //start_button.disabled = true;
    
	start_button.onclick =  function()
    {   
        var package_name = package_text.value;
        var launch_file = launch_file_text.value;
        var launch_args = args_text.value;
        var r=confirm("Start simulator on machine " + machine_name + "?");
        if (r==false)
        {
            return;
        }
        start_button.disabled = true;
        start_simulator(constellation_name, machine_name, package_name, launch_file, launch_args)
        setTimeout(function()
        {
            start_button.disabled = false;
        }, 10000);
        
    };
    
    
    var stop_button= document.createElement('input');
    //stop_button.disabled = true;
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('name','stop');
    stop_button.setAttribute('value','Stop');

    stop_button.onclick =  function()
    {
        // _stop_simulator(constellation_name, machine_name);
    	var r=confirm("Stop simulator on machine " + machine_name + "?");
        if (r==false)
        {
            return;
        }    
        stop_simulator(constellation_name, machine_name);
    };
    
    widget_div.appendChild(document.createTextNode("package: "));
    widget_div.appendChild(package_text);
    widget_div.appendChild(document.createTextNode("launch file: "));
    widget_div.appendChild(launch_file_text);
    widget_div.appendChild(document.createTextNode("args: "));
    widget_div.appendChild(args_text);
    
    widget_div.appendChild(start_button);
    widget_div.appendChild(stop_button);
    
*/
    
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        var color = "gray";
        
        if (data[glx_key] == "running")
        {
            if(data[simulator_key] == "running")
                color = "blue";
            else
                color = "red";
        }
        if(color == 'red' )
        {
            widget_div.querySelector("img").src = "/js/images/red_status.png";
            //stop_button.disabled = true;
            //start_button.disabled = false;
            
        }
        if(color == 'blue' )
        {
            widget_div.querySelector("img").src = "/js/images/blue_status.png";
            //stop_button.disabled = false;
            //start_button.disabled = true;
        }
        
        if(color == 'gray' )
        {
            widget_div.querySelector("img").src = "/js/images/gray_status.png";
            //stop_button.disabled = true;
            //start_button.disabled = true;
        }
            
        
    });
}

function _update_glx_state(widget_div, color, text)
{
    var status = status_img(color);
    var str = "";
    str += status;
    str += "<b>X and GL state:</b> ";
    str += text;
    widget_div.innerHTML = str;
    
}

function create_glx_state_widget(machine_div, constellation_name, machine_name,  glx_key)
{
    var widget_div = _create_empty_widget(machine_div, "glx");

    // default behaviour
    _update_glx_state(widget_div, "gray", "[waiting for update]");
    
    // reaction
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;

        if(data[glx_key] == "running")
        {
            _update_glx_state(widget_div, "blue", "running");
           
        }
        
        if(data[glx_key] == "pending")
        {
            _update_glx_state(widget_div, "orange", "testing");
        }
        
        if(data[glx_key] == "not running")
        {
            _update_glx_state(widget_div, "red", "not running");
        }
    });
}


/*
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
*/