
var machine_configurations = null;

function create_constellation_launcher_widget(div_name)
{   
    console.log('machine_launch_on_load_page div=' + div_name);
    var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs.py");
    machine_configurations = eval( '(' + x + ')' );
    
	var launch_div = document.getElementById(div_name);
	var str  = '<h2>Launch a machine constellation</h2>'; 
    str += '<select id="config_select" onchange="_launchSelectionChanged()";>'

    for(var configuration in machine_configurations)
    {
        str += '<option>' + configuration + '</option>';
    }

    str += '</select><button type="button" onclick="launch(_get_selectected_machine_config())">Launch</button><div id="config_div"></div>';
    
    launch_div.innerHTML = str;
    _launchSelectionChanged()
}


function launch(config)
{
    var r=confirm('Launch a new "' + config + '" constellation?' );
    if (r==false)
    {
        return;
    }
    
    launch_constelaltion(config);
    
}

function _get_selectected_machine_index()
{
    var i =document.getElementById("config_select").selectedIndex;
    return i;
}

function _get_selectected_machine_config()
{
    var i = _get_selectected_machine_index();
    var machine_config =document.getElementById("config_select").options[i].text;
    return machine_config;
}

function _launchSelectionChanged()
{
    var machine_config =_get_selectected_machine_config();
    var conf = machine_configurations[machine_config];
    
    var str = "<b>description:</b> " + conf.description + "<br>";
    document.getElementById("config_div").innerHTML = str;
}

