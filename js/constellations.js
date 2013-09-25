
function create_constellations_widget(div_name)
{
    console.log("create_constellations_widget " + div_name);
    var div = document.getElementById(div_name);
    var widget = document.createElement("div");
    widget.className = "top_level_container";
    widget.id = "constellations";
    var title_div = document.createElement("div");
    widget.appendChild(title_div);
    title_div.className = "top_level_title";
    var title = document.createTextNode("Constellations");
    title_div.appendChild(title);

    var div = document.getElementById(div_name);

    //var str = "<h2>Constellations</h2>";
    //div.innerHTML = str;

    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name)
        {
            var constellation = data.constellation_name;
            var configuration = data.configuration;
            var username = data.username;
            var gmt = data.gmt
            //data.constellation_config;
            var constellation_div =  div.querySelector("#"+constellation);
            if( constellation_div == null)
            {
            	create_constellation(div_name, configuration, constellation, data);
            }
        }
    });
    div.appendChild(widget);
}


function insert_constellation_div(div_name, configuration_name, constellation_name, username, gmt)
{
    var top_div = document.getElementById(div_name);
    var div = top_div.querySelector("#constellations");
    var nodes = div.childNodes;
    var node = null;
    for(var i=0; i<nodes.length; i++) 
    {
        node = nodes[i];
        var constellation_iter = node.id;
        if(constellation_iter == undefined)
            continue;
        var cmp = constellation_iter.localeCompare(constellation_name);
        // console.log(constellation_iter+ " comp " + constellation + " = " + cmp);

        // Found it :-) 
        if(cmp == 0)
            return node;

        // found where to create it :-)
        if(cmp > 0)
            break;

        // makes insertBefore at the end
        node = null;
    }

    var const_div = document.createElement("div");
    const_div.className = "second_level_container";
    const_div.id = constellation_name;
    
    var title_div = document.createElement("div");
    title_div.className = "second_level_title";
    const_div.appendChild(title_div);
    var title_txt = configuration_name + ": " +constellation_name  
    title_div.appendChild(document.createTextNode(title_txt));
    var top_div = document.createElement("div");

    top_div.id = "top";
    var title_str = " <h3 style=' margin-top:0; margin-bottom:0;'><table width='100%'><tr><td align='left'>";
    title_str    +=   constellation_name + "</td><td align='right'><FONT SIZE=2> Launched by " + username + " (UTC " + gmt + ")</FONT></td></tr>"; //"<tr><td><FONT SIZE=2>" + configuration_name + "</FONT></td><td align='right'><FONT SIZE=2> at UTC " + gmt + "</FONT></td></tr></table></h3>";
    const_div.appendChild(top_div);
    // div.insertBefore(top_div, node);

    var error_msg_div = document.createElement("div");
    error_msg_div.id = "error";
    error_msg_div.style.color = "red"; 
    top_div.appendChild(error_msg_div);


    // do not allow non admin users to terminate constellations
    if(get_user_info()['role'] == 'admin')
	{
        var terminate_button= document.createElement('input');
        terminate_button.setAttribute('type','button');
        terminate_button.setAttribute('value','Terminate');

        // do not allow users to Terminate constellations 
        terminate_button.onclick =  function()
        {   
        	var msg = "Warning!\n\nThis operation will wipe out all data";
        	msg += " on every computer in this constellation. The subsequent reload ";
        	msg += " operation will install a bare OS, perform diagnostics";
        	msg += " and will take about 1h."
        	msg += "\n\nType 'y' to confirm";
        	var agree = (prompt(msg, '') == 'y');
            if (agree==false)
            {
                return;
            }
            terminate_constellation(constellation_name);
            location.reload(true);
        };
        top_div.appendChild(terminate_button);
	}

	if(get_user_info()['role'] == 'admin')
	{
        
        var update_button= document.createElement('input');
        update_button.setAttribute('type','button');
        update_button.setAttribute('value','Update software');

        // do not allow users to Terminate constellations 
        update_button.onclick =  function()
        {   
        	var msg = "Update software on " + constellation_name + "?";
            msg += "\n\n";
            msg += "This operation will restart running processes, and ";
            msg += "may interrupt important tasks"; 
        
            var r = confirm(msg);
            
            if (r==false)
            {
                return;
            }
            update_constellation(constellation_name);
        };
        top_div.appendChild(update_button);
	}

    var machines_div = document.createElement("div");
    machines_div.id = "machines";
    const_div.appendChild(machines_div);
    // const_div.innerHTML = _get_constellation_div_str(div_name, configuration, constellation);
    div.insertBefore(const_div, node);
    return const_div;
}



// returns true if name is the name of one of the constellations
function _find_in_constellations(name, constellations)
{
	for (var i=0; i < constellations.length; i++)
	{
		var c_name = constellations[i].constellation_name;
		if(c_name == name)
		{
			return true;
		}
	}
	return false;
}

function remove_old_constellations(constellations)
{
	var constellation_widget_div = document.querySelector("#constellations_div");
	var constellations_div = constellation_widget_div.querySelector("#constellations");
	// skip the first chid, i.e. "<h2>Constellations</h2>"
	for (var i=1; i < constellations_div.childElementCount; i++)
	{
		var constellation_div = constellations_div.childNodes[i];
		var id = constellation_div.id;
		var exists = _find_in_constellations(id, constellations);
		if (!exists)
		{
			console.log(id + " DOES NOT EXISTS ANYMORE");
			constellations_div.removeChild(constellation_div);
		}
	}
}
