
var machine_configurations = null;


function create_constellation_launcher_widget(div_name)
{   
    console.log('machine_launch_on_load_page div=' + div_name);
    var machine_configurations = get_configurations();

    var div = document.getElementById(div_name);
    div.setAttribute("class","module_content")
    div.setAttribute("style","overflow:hidden;")
    
    var desc = document.createElement("p");
    desc.setAttribute("style", "font: bold 12px;");
    
    var wrapper_select = document.createElement('fieldset');
    wrapper_select.setAttribute('style', 'width:48%; margin-right: 3%; margin-top: 0;');
    var label1 = document.createElement('label');
    label1.innerHTML = 'Constellation';
    
    wrapper_select.appendChild(label1);
    
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
    
    wrapper_select.appendChild(configs_select);
    
    var launch_button= document.createElement('input');
    launch_button.setAttribute('style','background: #3573c0; margin-top:4px; color: #fff; padding:2px 6px;\
                                  cursor: pointer; border-radius: 4px; -moz-border-radius: 4px; -webkit-border-radius: 4px;');
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
    
    //var title = document.createElement('h2');
    //title.innerHTML = 'Launch a machine constellation';
    
    configs_select.onchange();
    
    //div.appendChild(title);
    div.appendChild(wrapper_select);
    div.appendChild(desc);
    div.appendChild(launch_button);
    
    //alert(div);
    
}

function _reenable(div_name)
{
    var div = document.getElementById(div_name);
    var btn = div.querySelector('input')
    btn.disabled = false;
}
