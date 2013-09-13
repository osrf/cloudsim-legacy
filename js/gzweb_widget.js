

function create_gzweb_widget(machine_div,
						     constellation_name,
						     machine_name,
							 glx_key,
							 simulator_key,
							 gz_web_key)
{
	// roslaunch atlas_utils atlas_position_controllers.launch
    var package_name = "atlas_utils";//"drc_robot_utils";
    var launch_file = "vrc_task_1.launch"; // "drc_robot.launch";
    var launch_args = "";
    var widget_div = _create_empty_widget(machine_div, "gzweb");

    var status = status_img("gray");
    widget_div.innerHTML = status + "<b>WebGL interface</b>";

    var start_button = document.createElement('input');
    start_button.setAttribute('type','button');
    start_button.setAttribute('value','Start');
    start_button.onclick =  function()
    {
    	start_web_tools(constellation_name);
    	start_button.disabled = true;
        setTimeout( function(){
        	start_button.disabled = false;
            }, 3000); // setTimeOut
    }
    widget_div.appendChild(start_button);

    var stop_button = document.createElement('input');
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('value','Stop');
    stop_button.onclick =  function()
    {
    	stop_web_tools(constellation_name);
    }
    widget_div.appendChild(stop_button);
 
    var link = document.createElement('span');
    //link.innerHTML = "hello";
    widget_div.appendChild(link);
    
    var count = 0;
    var link_txt = "";
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;

        var gzweb_running = false;
        var simulator_running = false;
        
        // X and simulator must be running
        if (data[glx_key] == "running")
        {
            if(data[simulator_key] == "running")
            {
            	simulator_running = true;
            }
            else
            {
            	widget_div.querySelector("img").src = "/js/images/red_status.png";
            	link_txt = "";
            	if(link.innerHTML != link_txt)
            		link.innerHTML = link_txt;
            	stop_button.disabled = true;
                start_button.disabled = true;
                return;
            }
        }
        if (simulator_running == false)
        {
        	widget_div.querySelector("img").src = "/js/images/red_status.png";
        	link_txt = "";
        	if(link.innerHTML != link_txt)
        		link.innerHTML = link_txt;
        	stop_button.disabled = true;
            start_button.disabled = true;        	
        	return;
        }
        
        if (data[gz_web_key] == "running")
        {
            widget_div.querySelector("img").src = "/js/images/blue_status.png";
            var web_url = data['router_public_ip'] + ":8080";
            var notebook_url = data['router_public_ip'] + ":8888";
            link_txt = '<a href=http://' + web_url + '>3D view</a> ' ;
            link_txt += '<a href=http://' + notebook_url + '>Python notebook</a>' ;
            if (link.innerHTML != link_txt)
            {
            	link.innerHTML = link_txt;
            }
            stop_button.disabled = false;
            start_button.disabled = true;
        }
        else if (data[gz_web_key] == "starting")
        {
        	colors =  ["/js/images/blue_status.png", "/js/images/blue_status.png"];
        	var color = colors[count % colors.length];
        	widget_div.querySelector("img").src = color;
            if (count == 100) 
                count =0;
            else 
                count ++;
        }	
        else
        {
        	link.innerHTML = "";
            widget_div.querySelector("img").src = "/js/images/gray_status.png";
            stop_button.disabled = true;
            start_button.disabled = false;
            return;
        }
    });
}
