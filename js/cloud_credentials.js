
var machine_configurations = null;

function add_cloud_default_az_widget(div_name)
{
    var div = document.getElementById(div_name);
    
    var widget = document.createElement("div");
    widget.className = "top_level_container";
    
    var title_div = document.createElement("div");
    title_div.className = "top_level_title";
    
    widget.appendChild(document.createElement('br'));
    
    var title = document.createTextNode("Amazon Web Services default availability zones");
    title_div.appendChild(title);
    
    widget.appendChild(title_div);
    widget.appendChild(document.createElement('br'));
    
    var default_azs = {"us_east_1":"us_east_1b"};
    try
    {
    	var default_azs = get_default_aws_az();	
    	
    }
    catch(e)
    {
    	console.log("can't get default values for availability zones: " + e);
    }
    
    var us_east1_az_select = az_select(widget, "US East (N. Virginia): ",
    		["any", "us_east_1a", "us_east_1b", "us_east_1c", "us_east_1d"],
    		default_azs["us_east_1"]);
    var eu_west_az_select = az_select(widget, "EU (Ireland): ",
    		["any", "eu_west_1a", "eu_west_1b", "eu_west_1c"],
    		default_azs["eu_west_1"]);
    var us_west1_az_select = az_select(widget, "US West (Oregon): ",
    		["any", "eu_west_1a", "eu_west_1b", "eu_west_1c"],
    		default_azs["eu_west_1"]);

    var override_btn = document.createElement('input');

    override_btn.setAttribute('type','button');
    override_btn.setAttribute('value','Override');

    override_btn.onclick =  function() {
        var i = us_east1_az_select.selectedIndex;
        var us_east1 = us_east1_az_select.options[i].text;
        var eu_west = eu_west_az_select.options[eu_west_az_select.selectedIndex].text;
        var us_west1 = us_west1_az_select.options[us_west1_az_select.selectedIndex].text;
        
        alert(us_east1 + ", " + eu_west + ", " + us_west1);
    }
    
    // widget.appendChild(document.createElement('br'));
    widget.appendChild(override_btn);
    widget.appendChild(document.createElement('br'));
    widget.appendChild(document.createElement('br'));
    widget.appendChild(document.createTextNode("Set the default Availability zone for AWS regions"));

    div.appendChild(widget);
}

function az_select(widget, region_name, az_list, value)
{	
	widget.appendChild(document.createTextNode(region_name));
	
	var az_select = document.createElement('select');
    widget.appendChild(az_select);
    for (var i=0; i < az_list.length; i++)
    {
    	var option = document.createElement("option");
    	var az_name = az_list[i];
    	option.text = az_name;
    	option.value = az_name;
    	az_select.add(option, null);
    	// chec if it is the selected value
    	if (value == az_name)
    	{
    		az_select.selectedIndex = i;
    	}
    }
    widget.appendChild(az_select);
  //  widget.appendChild(document.createElement('br'));
    
    return az_select;
}

function add_cloud_credentials_widget(place_holder_div_name)
{

    var launch_div = document.getElementById(place_holder_div_name);
    launch_div.className = "top_level_container";
    var str  = '<h2>Amazon Web Services credentials</h2>'; 
    str += '';
    str += 'Access key <input type="text" name="access_key"/>';
    str += 'Secret access key <input type="text" name="secret_access_key"/>';
    str += '<button type="button" onclick="_cred_click(\'';
    str += place_holder_div_name;
    str += '\');">Override</button><br><br>Set new AWS credentials and availability zone. Those changes will be applied on the new constellations';
    
    launch_div.innerHTML = str;
    console.log('cloud_credentials_on_load_page:' +  place_holder_div_name);
}

function _cred_click(div_name)
{
    console.log('_cred_click')
    var div = document.getElementById(div_name);
    
    var access = div.querySelectorAll("input")[0].value;
    var secret_access = div.querySelectorAll("input")[1].value;
    var r = change_aws_credentials(access, secret_access);
    
    alert(r['msg']);
}

