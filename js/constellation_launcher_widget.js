
function create_constellation_launcher_widget(div_name)
{
    var div = document.getElementById(div_name);
    var widget = document.createElement("div");
    widget.className = "top_level_container";
    var title_div = document.createElement("div");
    widget.appendChild(title_div);
    title_div.className = "top_level_title";
    var title = document.createTextNode("Constellation provisioning");
    title_div.appendChild(title);

	var machine_configurations = [];
    try
    {
        machine_configurations = get_configurations();

    }
    catch(err)
    {
        console.log(err);
    }
    var configs_select = document.createElement('select');
    widget.appendChild(configs_select);
    for(var configuration in machine_configurations)
    {        
        var option=document.createElement("option");
        option.text=configuration;
        configs_select.add(option,null);
	}
	
	var desc = document.createElement("div");
    configs_select.onchange = function()
    {
    	var i = configs_select.selectedIndex;
        var config = configs_select.options[i].text;
        var description = machine_configurations[config].description;
        
        desc.innerHTML = "<br>"+description;
    }

    var launch_button= document.createElement('input');
    widget.appendChild(launch_button);
    launch_button.setAttribute('type','button');
    launch_button.setAttribute('value','Deploy');
	
	widget.appendChild(desc);

    launch_button.onclick =  function() {
            var i = configs_select.selectedIndex;
            var config = configs_select.options[i].text;
            
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
             launch_constellation(config);
              // add everything to the page
          };
    div.appendChild(widget);
}
