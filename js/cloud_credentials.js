
// var machine_configurations = null;

function add_cloud_credentials_widget(place_holder_div_name)
{
    var widget = document.getElementById(place_holder_div_name);
    widget.className = "top_level_container";

    // Title div
    var title_div = document.createElement("div");
    title_div.className = "top_level_title";
    widget.appendChild(document.createElement('br'));
    var title = document.createTextNode("Amazon Web Services credentials");
    title_div.appendChild(title);
    widget.appendChild(title_div);
    widget.appendChild(document.createElement('br'));    

    // access key
    widget.appendChild(document.createTextNode('Access key: '));
    var access_key_input = document.createElement('input');
    access_key_input.type = "text";
    widget.appendChild(access_key_input);

    // secret key
    widget.appendChild(document.createTextNode('Secret key: '));
    var secret_key_input = document.createElement('input');
    secret_key_input.type = "text";
    widget.appendChild(secret_key_input);

    var sub_title = document.createElement('h3');
    sub_title.innerHTML = "Default availability zones:";
    widget.appendChild(sub_title);

    default_azs ={"us_east_1": "any", "eu_west_1": "any", "us_west_2": "any"}
	var us_east_1_select = add_az_selector(widget,
			"us_east_1",
			"US East (N. Virginia): ",
			"any",
    		["any", "us_east_1a", "us_east_1b", "us_east_1c", "us_east_1d"]);
	var eu_west_1_select = add_az_selector(widget,
					"eu_west_1",
					"EU (Ireland): ",
					"any",
					["any", "eu_west_1a", "eu_west_1b", "eu_west_1c"]);
	var us_west_2_select = add_az_selector(widget,
			"us_west_2",
			"US West (Oregon): ",
			"any",
			["any", "us_west_2a", "us_west_2b", "us_west_2c"]);

	var override_az_btn = document.createElement('input');
	override_az_btn.setAttribute('type','button');
	override_az_btn.setAttribute('value','Override');
    widget.appendChild(override_az_btn);

    override_az_btn.onclick = function()
    {
    	var i = us_east_1_select.selectedIndex;
    	var j = eu_west_1_select.selectedIndex;
    	var k = us_west_2_select.selectedIndex;
    	
    	var us_east_1_az = us_east_1_select.options[i].value;
    	var us_west_2_az = eu_west_1_select.options[j].value;
    	var eu_west_1_az = us_west_2_select.options[k].value;
    	
        var access = access_key_input.value;
        var secret_access = secret_key_input.value;
        var r = change_aws_credentials(access,
        								secret_access,
        								us_east_1_az,
        								us_west_2_az,
        								eu_west_1_az); 
        
    	
    }
}

function add_az_selector(widget, region_name, title, current_value, az_list)
{   
	// widget.appendChild(document.createElement('br'));    
	widget.appendChild(document.createTextNode(title));
	
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
    	if (current_value == az_name)
    	{
    		az_select.selectedIndex = i;
    	}
    }
    widget.appendChild(az_select);
    return az_select;
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

