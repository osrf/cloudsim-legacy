

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
	str +='></div>';
	
	str += "</div> ";
	
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

