

function machines_on_load_page()
{
    
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
	str += _get_mach_style();
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

function add_machine_reboot_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
    var str = "<div id='" + widget_name + "'";
	str += _get_widget_style();
	str += ">";
	str += widget_name;
    str += "<button>Reboot</button>";
	str += "</div>";
	

	var div = document.getElementById(div_name);
	
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
	machine.innerHTML += str;
}

function add_machine_state_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
	
	var div = document.getElementById(div_name);
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);

    var str = "<div id='" + widget_name + "'";
	str += _get_widget_style();
	str += ">";
	str += widget_name;
	var status = status_img("gray");
    str += status;
	str += "</div>";
	
	machine.innerHTML += str;
}

function add_machine_hostname_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
	var div = document.getElementById(div_name);
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);

    var str = "<div id='" + widget_name + "'";
	str += _get_widget_style();
	str += ">";
	str += widget_name;
    str += "<b>IP</b>xxx.xxx.xxx ("
    str += "<b>AWS ID</b>xxxxxx) ";
    str += '<a href="/cloudsim/inside/cgi-bin/machine_zip_download.py?machine=';
    str += machine_name;
    str += '">Download keys</a>';
	str += "</div>";
	
	machine.innerHTML += str;	
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






