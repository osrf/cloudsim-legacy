
function create_constellation_launcher_widget(div_name)
{
	var machine_configurations = {};
    try
    {
        machine_configurations = get_configurations();

    }
    catch(err)
    {
        console.log(err);
    }

	var div = document.getElementById(div_name);
    var widget = document.createElement("div");
    widget.className = "top_level_container";

    var title_div = document.createElement("div");
    widget.appendChild(title_div);
    title_div.className = "top_level_title";
    var title = document.createTextNode("Constellation provisioning");
    title_div.appendChild(title);
    widget.appendChild(document.createElement('br'));
	
    // cloud service provider selection
	var cloud_provider_title = document.createElement('b');
	cloud_provider_title.innerHTML = "Cloud service provider:";
	widget.appendChild(cloud_provider_title);
	var cloud_service_select = document.createElement('select');
    widget.appendChild(cloud_service_select);
    widget.appendChild(document.createElement('br'));
    
	// Region selection
    var region_title = document.createElement('b');
	region_title.innerHTML = "Region:";
	widget.appendChild(region_title);
	var region_select = document.createElement('select');
    widget.appendChild(region_select);
    widget.appendChild(document.createElement('br'));

    // Configuration selection
    var config_title = document.createElement('b');
	config_title.innerHTML = "Configuration:";
	widget.appendChild(config_title);
    var config_select = document.createElement('select');
    widget.appendChild(config_select);

    var launch_button= document.createElement('input');
    widget.appendChild(launch_button);
    launch_button.setAttribute('type','button');
    launch_button.setAttribute('value','Deploy');

    // description (and options in the future) pane
    var desc = document.createElement("div");
    widget.appendChild(desc);
	
    cloud_service_select.onchange = function()
    {
        // find the current cloud creds account
    	var i = cloud_service_select.selectedIndex;
        var service = cloud_service_select.options[i].text;
        console.log("service: " + service);
        
        // clear regions and list all regions for that creds.
        var count = region_select.options.length;
        for (var i=0; i < count; i++)
        {
        	region_select.options.remove(0);
        }
        // add regions for selected cloud provider
        var service_data = machine_configurations[service];
        for (var region in service_data)
        {
        	console.log(region);
        	var option=document.createElement("option");
        	option.text=region;
        	option.value = region;
        	region_select.add(option,null);
        }
        region_select.onchange();
    }
    
    region_select.onchange = function()
    {
        // clear configurations
        count = config_select.options.length;
        for (var i=0; i < count; i++)
        {
        	config_select.options.remove(0);
        }

        var service = cloud_service_select.options[cloud_service_select.selectedIndex].text;
        // add configurations available in this region
        var current_region = region_select.selectedIndex;
        var region = region_select.options[current_region].text;
                
        var configuration_list = machine_configurations[service][region];
        for(var i=0; i < configuration_list.length; i++)
        {
        	var config = configuration_list[i];
        	var option=document.createElement("option");
        	var name = config.name;
        	var desc = config.description;
        	option.text=name;
        	option.value=desc;
        	config_select.add(option,null);
        }
        config_select.onchange();    	
    }

	config_select.onchange = function()
    {
    	var i = config_select.selectedIndex;
    	if(i >= 0)
    	{
            var config_name = config_select.options[i].text;
            var description = config_select.options[i].value; 
            console.log("DESC " + description);
            desc.innerHTML = "<br>"+description;
            launch_button.disabled = false;
    	}
    	else
    	{
    		// nothing available
    		desc.innerHTML = "";
    		launch_button.disabled = true;
    	}
    }

   // set the list of credentials 
   for(var provider_name in machine_configurations)
   {
       var option = document.createElement("option");
       option.text = provider_name;
       option.value = machine_configurations[provider_name];
       cloud_service_select.add(option, null); 
   }
   // trigger the updates
   cloud_service_select.onchange();
   

   
   launch_button.onclick =  function() {
            var i = configs_select.selectedIndex;
            var config = configs_select.options[i].text;
            var j = cloud_service_select.selectedIndex;
            var cloud_provider = cloud_service_select.options[j].value;

            var msg = 'Deploy a new "' + config + '" constellation?';
            msg += "\n\n";
            msg += "This operation may incur charges";
            msg += "";
            var r=confirm(msg);
            if (r==false)
            {
                return;
            }
            launch_button.disabled = true;
            setTimeout( function(){
                launch_button.disabled = false;
                }, 3000); // setTimeOut
             launch_constellation(cloud_provider, config);
              // add everything to the page
          };
    div.appendChild(widget);
}
