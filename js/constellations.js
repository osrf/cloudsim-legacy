
function create_constellations_widget(div_name)
{
    console.log("create_constellations_widget " + div_name);
    var div = document.getElementById(div_name);
    
    
    var str = "<h2>Constellations</h2>";
    div.innerHTML = str;

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
                create_constellation(div_name, configuration, constellation, username, gmt);
            }
        }
    });
}



function insert_constellation_div(div_name, configuration_name, constellation_name, username, gmt)
{
    var div = document.getElementById(div_name);
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
    const_div.id = constellation_name;
    _set_const_style(const_div.style);

    var top_div = document.createElement("div");

    top_div.id = "top";

    //var title_str = " <h3 style=' margin-top:0; margin-bottom:0;'><table width='100%'><tr><td align='left'>";
    //title_str    +=   constellation_name + "</td><td align='right'><FONT SIZE=2> Launched by " + username + "</FONT></td></tr><tr><td><FONT SIZE=2>" + configuration_name + "</FONT></td><td align='right'><FONT SIZE=2> at GMT " + gmt + "</FONT></td></tr></table></h3>";
    
    var title_str = " <h3 style=' margin-top:0; margin-bottom:0;'><table width='100%'><tr><td align='left'>";
    title_str    +=   constellation_name + "</td><td align='right'><FONT SIZE=2> Launched by " + username + " (UTC " + gmt + ")</FONT></td></tr>"; //"<tr><td><FONT SIZE=2>" + configuration_name + "</FONT></td><td align='right'><FONT SIZE=2> at UTC " + gmt + "</FONT></td></tr></table></h3>";

    
    
    top_div.style.backgroundColor ="#44497a";
    top_div.style.borderTopLeftRadius = "15px";
    top_div.style.borderTopRightRadius = "15px";
    top_div.style.color = "white";
    top_div.style.marginTop = "0";
    top_div.style.color = "0";
    top_div.style.float = "left";
    top_div.style.width = "100%";
    top_div.style.height = "100%";
    top_div.innerHTML = title_str;
    
    const_div.appendChild(top_div);
    
    // div.insertBefore(top_div, node);


    var msg_div = document.createElement("div");
    msg_div.id = "error";
    msg_div.style.color = "red"; 
    msg_div.style.float = "left";
    const_div.appendChild(msg_div);


    // do not allow simple users to terminate constellations
    if(get_user_info()['role'] != 'user')
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


function constellation_remove(div_name, constellation_name)
{
    var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    div.removeChild(constellation);   
}


function _set_const_style(style)
{
    style.width = "98%";
    style.float = "left";
    style.border="1px solid #535453";
    style.borderRadius = "15px";
    style.margin = "1%";
    style.backgroundColor = "#a8a7a7"; // f1f1f2
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
	constellations_div = document.querySelector("#constellations_div");
	// skip the first chid, i.e. "<h2>Constellations</h2>"
	for (var i=1; i < constellations_div.childElementCount; i++)
	{
		var id = constellations_div.childNodes[i].id;
		var exists = _find_in_constellations(id, constellations);
		if (!exists)
		{
			console.log(id + " DOES NOT EXISTS ANYMORE");
			constellation_remove("constellations_div", id)
		}
		
	}

}
