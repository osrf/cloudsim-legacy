var GZWEB_PORT = 8080;

function create_start_stop_service(machine_div,
							constellation_name,
							machine_name,
							title,
							link_txt,
							service_state_key,  // "running", "starting", "stopping"
							start_func,
							stop_func,
							btn_timeout,
							is_sim_service)
{
	var glx_key = "sim_glx_state";
	var simulator_key = "gazebo";
	var ip_key = "sim_public_ip";
	console.log("create_sim_service '" + title + "' for " + constellation_name);
	
    var widget_div = _create_empty_widget(machine_div, service_state_key);
    var status = status_img("gray");
    widget_div.innerHTML = status + "<b>" + title +"</b>";

    // start button
    var start_button = document.createElement('input');
    start_button.setAttribute('type','button');
    start_button.setAttribute('value','Start');
    start_button.onclick =  function()
    {
    	start_func(constellation_name);
    	start_button.disabled = true;
        setTimeout( function(){
        	start_button.disabled = false;
            }, btn_timeout); // setTimeOut
    }
    widget_div.appendChild(start_button);

    // stop button
    var stop_button = document.createElement('input');
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('value','Stop');
    stop_button.onclick =  function()
    {
    	stop_func(constellation_name);
    	stop_button.disabled = true;
        setTimeout( function(){
        	stop_button.disabled = false;
         }, btn_timeout); // setTimeOut
    }
    widget_div.appendChild(stop_button);
    
    var link = document.createElement('span');
    widget_div.appendChild(link);
    
    var count = 0;
    var img = widget_div.querySelector("img");
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;       
        if (count == 100) 
            count =0;
        else 
            count ++;     
        var simulator_running = false;        
        var service_state = data[service_state_key];

        // X and simulator must be running
        if (data[glx_key] == "running")
        {
            if(data[simulator_key] == "running")
            {
            	simulator_running = true;
            }
        }
        
        if(is_sim_service)
        {
        	if (simulator_running == false)
	        {
	        	img.src = "/js/images/red_status.png";
	        	if(link.innerHTML != "")
	        		link.innerHTML = "";
	        	stop_button.disabled = true;
	            start_button.disabled = true;        	
	        	return;
	        }      
        }
        if (service_state == "running")
        {
            img.src = "/js/images/blue_status.png";
            if (link.innerHTML != link_txt)
            {
            	link.innerHTML = link_txt;
            }
            stop_button.disabled = false;
            start_button.disabled = true;
        }
        else if (service_state == "starting")
        {
        	colors =  ["/js/images/gray_status.png", "/js/images/blue_status.png"];
        	var color = colors[count % colors.length];
        	img.src = color;
        }	
        else if (service_state == "stopping")
        {
        	colors =  ["/js/images/gray_status.png", "/js/images/red_status.png"];
        	var color = colors[count % colors.length];
        	img.src = color;
        }
        else
        {
        	if(link.innerHTML != "")
        		link.innerHTML = "";
            img.src = "/js/images/gray_status.png";
            stop_button.disabled = true;
            start_button.disabled = false;
            return;
        }
    });
}


function create_cloudsim_notebook_widget(machine_div,
                                         constellation_name,
                                         machine_name,
                                         ip_address)
{
    var title = "iPython Notebook";
    var service_state_key = "gzweb";
    var service_state_key = "cloudsim_notebook";  // gz_web_key
    var btn_timeout = 10000;
    var link_txt = '<a href=http://' + ip_address + ':' + GZWEB_PORT;
    link_txt += ' target="_blank" >Python notebook</a>';
    var start_func = function(){
        start_cloudsim_notebook(constellation_name);
    }

    var stop_func = function(){
        stop_cloudsim_notebook(constellation_name);
    }
    create_start_stop_service(machine_div,
                              constellation_name,
                              machine_name,
                              title,
                              link_txt,
                              service_state_key,
                              start_func,
                              stop_func,
                              btn_timeout,
                              false);
}


function create_gzweb_widget(machine_div,
	     constellation_name,
	     machine_name,
		 ip_address)
{
	var title = "WebGL interface";
	var service_state_key = "gzweb"; // gz_web_key
	var btn_timeout = 10000;

    var link_txt = '<a href=http://' + ip_address + ":8888" + ' target="_blank" >3D view</a> ' ;
    
	var start_func = function(){
		start_web_tools(constellation_name);
	}
	
	var stop_func = function(){
		stop_web_tools(constellation_name);
	}

	create_start_stop_service( machine_div,
						constellation_name,
						machine_name,
						title,
						link_txt,
						service_state_key,
						start_func,
						stop_func,
						btn_timeout,
						true);
}
