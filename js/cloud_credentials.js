
var machine_configurations = null;

function cloud_credentials_on_load_page(launch_div_name)
{

	var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs.py");
    machine_configurations = eval( '(' + x + ')' );
    
	var launch_div = document.getElementById(launch_div_name);
	var str  = '<h2>Amazon EC2 credentials</h2>'; 
    str += '<select id="config_select" onchange="_launchSelectionChanged()";>'

    for(var configuration in machine_configurations)
    {
        str += '<option>' + configuration + '</option>';
    }

    str += '</select><button type="button" onclick="launch(_get_selectected_machine_config())">Launch</button><div id="config_div"></div>';
    
    launch_div.innerHTML = str;

    var div_name = "log_div";
    log_to_div(div_name, "on_load_page");
    

    _launchSelectionChanged()
}

function change_credentials(machine_config)
{
    machine_index = 0;
    var machine_div_name =  "machine_div_" + machine_index;

    var r=confirm("Launch?");
    if (r==false)
    {
        // x="You pressed Cancel!";
        return;
    }

    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=launch&machine_config=' + _get_selectected_machine_config();
    log_to_div("log_div", url);
    msg = httpGet(url);
    //alert(msg);
    log_to_div("log_div", "");
    log_to_div("log_div", msg);
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

