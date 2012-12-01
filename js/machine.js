

function machines_on_load_page()
{
    console.log("machines_on_load_page");
    
}

function get_machine_names(div_name, constellation)
{
    var machines_div = constellation_get_machines_div(div_name, constellation);
    
    var machines = [];
    var nodes = machines_div.childNodes; // getElementsByTagName('div');
    for(var i=0; i<nodes.length; i++) {
        var node = nodes[i];
        var title = node.id;
        if(title != undefined)
        {
            machines.push(title);
        }
    }
    return machines;
}

function machine_add(div_name, constellation_name, machine_name)
{
	var str = "<div id='" + machine_name + "'";
	str += _get_mach_style();
	str += "> ";
	
	
	str += '<div id="top" style="width = 100%; float:left; border-top-left-radius:10px; border-top-right-radius:15px; background-color:#44497a; width:100%; float:left;" ">' // background-color:#FFA500;
	str +=    "<h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
	str +=    machine_name + "</center></h3>";    
    str += '</div>' // top
    
    
	str += '<div id="widgets"';
	str += _get_machine_widgets_style();
	str +='></div>'; // widgets
	
	str += "</div> "; // machine
	
	var machines_div = constellation_get_machines_div(div_name, constellation_name);
	machines_div.innerHTML += str;
    
}

function machine_get_widget_div(div_name, constellation_name, machine_name)
{
	var machines_div = constellation_get_machines_div(div_name, constellation_name);
	var machine_div = machines_div.querySelector("#" + machine_name);
	var widgets_div = machine_div.querySelector("#widgets");
	return widgets_div;
}


///////////////////

function add_machine_lifecycle_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
	
    var str = "<div id='" + widget_name + "'";
	str += _get_widget_style();
	str += ">";
	// str += widget_name;
	str += "<button>Reboot</button>";
	str += "<button>Start</button>";
	str += "<button>Stop</button>";
	str += "</div>";
	
	var div = document.getElementById(div_name);
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
	machine.innerHTML += str;
}

function _update_machine_state(widget_div, color, text)
{
    var str = ""; // widget_name;
    var status = status_img(color);
    str += status;
    str += text;
    widget_div.innerHTML = str;
    
}

function add_machine_state_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
    var div = document.getElementById(div_name);
    var machine = machine_get_widget_div(div_name, constellation_name, machine_name);

    var str = "<div id='" + widget_name + "'";
    str += _get_widget_style();
    str += ">";
    str += "</div>";
    machine.innerHTML += str;
    
    var widget_div = get_widget_div(div_name, constellation_name, machine_name, widget_name);
    _update_machine_state(widget_div, "gray", "[waiting for update]");
    
    $.subscribe("/cloudsim", function(event, data){
        if(data.type == 'cloud')
        {
            var color = "red";
            if(data.result == 'success')
            color = "blue";
            _update_machine_state(color, data.state);
        }
        
    });
    
}

function _update_hostname_widget(widget_div, constellation_name, machine_name, ip, aws_id)
{
		
    var str = "";
    str += "<b>IP</b> " + ip + " ("
    str += "<b>AWS ID</b> " + aws_id +") ";
    str += '<a href="/cloudsim/inside/cgi-bin/machine_zip_download.py';
    str += '?constellation=' + constellation_name;
    str += '&machine=' + machine_name;
    str += '">Download keys</a>';
    widget_div.innerHTML = str;
}

function add_machine_hostname_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
	var div = document.getElementById(div_name);
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
    
    var str = "<div id='" + widget_name + "'";
    str += _get_widget_style();
    str += ">";
    // str += _get_hostname_widget_html(machine_name, "xxx.xxx.xxx", "x-xxxxx")
    str += "</div>";
    machine.innerHTML += str;
    
    var widget_div = get_widget_div(div_name, constellation_name, machine_name, widget_name);
    _update_hostname_widget(widget_div, constellation_name, machine_name, "xxx.xxx.xxx", "x-xxxxx");
    
}

function _get_mach_style()
{
    var str = "";
    str += ' style="';
    str += ' width:98%; float:left; border-radius: 15px;';
    str += ' border: 1px solid black;';
    str += 'margin:1%;';
    //str += 'margin-bottom:10px;';
    str += '"'; 
    return str;
} 

function _get_machine_widgets_style()
{
    var str = '';
    str += ' style="';
    str += ' width:98%; float:left;';
    // str += ' border-radius: 15px;';
    //str += ' border: 1px solid black;';
    str += ' margin:1%;';
    //str += 'margin-bottom:10px;';
    str += '"'; 
    return str;	
}




