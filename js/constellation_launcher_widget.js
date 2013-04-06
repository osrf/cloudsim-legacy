
var machine_configurations = null;


function create_constellation_launcher_widget(div_name)
{   
    console.log('machine_launch_on_load_page div=' + div_name);
    var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs.py");
    machine_configurations = eval( '(' + x + ')' );

    var div = document.getElementById(div_name);
    
    var desc = document.createElement("div");
    desc.setAttribute("style", "width: 100%; float: left; height: 10px; padding: 5px 0px 0px 0px; position: relative;");
    
    var configs_select = document.createElement('select');
    for(var configuration in machine_configurations)
    {        
        var option=document.createElement("option");
        option.text=configuration;
        configs_select.add(option,null);
    }
    configs_select.onchange = function()
    {
    	var i = configs_select.selectedIndex;
        var config = configs_select.options[i].text;
        var description = machine_configurations[config].description;
        
        desc.innerHTML = description;	
    }
    
    var launch_button= document.createElement('input');
    launch_button.setAttribute('type','button');
    launch_button.setAttribute('value','Launch');
    
    
	launch_button.onclick =  function()
    {   
        var i = configs_select.selectedIndex;
        var config = configs_select.options[i].text;
        var r=confirm('Launch a new "' + config + '" constellation?' );
        if (r==false)
        {
            return;
        }
       
       launch_button.disabled = true;
       setTimeout('_reenable("' + div_name+ '");', 3000);
       launch_constellation(config);
       
    };
    
    var title = document.createElement('h2');
    title.innerHTML = 'Launch a machine constellation';
    
    configs_select.onchange();
    
    div.appendChild(title);
    div.appendChild(configs_select);
    div.appendChild(launch_button);
    div.appendChild(desc);
    
}

function _reenable(div_name)
{
    var div = document.getElementById(div_name);
    var btn = div.querySelector('input')
    btn.disabled = false;
}
