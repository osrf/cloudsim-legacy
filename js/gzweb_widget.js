

function create_gzweb_widget(machine_div,
						     constellation_name,
						     machine_name,
							 glx_key,
							 simulator_key,
							 gz_web_key,
							 ip_key)
{
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
            }, 10000); // setTimeOut
    }
    widget_div.appendChild(start_button);

    var stop_button = document.createElement('input');
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('value','Stop');
    stop_button.onclick =  function()
    {
    	stop_web_tools(constellation_name);
    	stop_button.disabled = true;
        setTimeout( function(){
        	stop_button.disabled = false;
         }, 5000); // setTimeOut
    }
    widget_div.appendChild(stop_button);
 
    var link = document.createElement('span');
    //link.innerHTML = "hello";
    widget_div.appendChild(link);
    
    var count = 0;
    var link_txt = "";
    var img = widget_div.querySelector("img");
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        
        if (count == 100) 
            count =0;
        else 
            count ++;
        
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
            	img.src = "/js/images/red_status.png";
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
        	img.src = "/js/images/red_status.png";
        	link_txt = "";
        	if(link.innerHTML != link_txt)
        		link.innerHTML = link_txt;
        	stop_button.disabled = true;
            start_button.disabled = true;        	
        	return;
        }
        
        if (data[gz_web_key] == "running")
        {
            img.src = "/js/images/blue_status.png";
            var web_url = data[ip_key] + ":8080";
            var notebook_url = data[ip_key] + ":8888";
            link_txt = '<a href=http://' + web_url + ' target="_blank" >3D view</a> ' ;
            link_txt += '<a href=http://' + notebook_url + ' target="_blank" >Python notebook</a>' ;
            if (link.innerHTML != link_txt)
            {
            	link.innerHTML = link_txt;
            }
            stop_button.disabled = false;
            start_button.disabled = true;
        }
        else if (data[gz_web_key] == "starting")
        {
        	colors =  ["/js/images/gray_status.png", "/js/images/blue_status.png"];
        	var color = colors[count % colors.length];
        	img.src = color;
        }	
        else if (data[gz_web_key] == "stopping")
        {
        	colors =  ["/js/images/gray_status.png", "/js/images/red_status.png"];
        	var color = colors[count % colors.length];
        	img.src = color;
        }
        else
        {
        	link.innerHTML = "";
            img.src = "/js/images/gray_status.png";
            stop_button.disabled = true;
            start_button.disabled = false;
            return;
        }
    });
}
