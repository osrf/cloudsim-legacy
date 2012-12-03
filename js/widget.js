

function widget_add(div_name, constellation_name, machine_name, widget_type, widget_name)
{

	
	var str = "<div id='" + widget_name + "'";

	str += _get_widget_style();

	str += "> ";
	str += widget_name;
	str += "</div> ";
	var div = document.getElementById(div_name);

	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
	machine.innerHTML += str;

	
}

function get_widget_div(div_name, constellation_name, machine_name, widget_name)
{
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
	widget = machine.querySelector("#" + widget_name);
	return widget;
}

/*
function _get_widget_style()
{
    var str = ' style="width:100%; float:left;';
//    str +='  border: 1px solid black;';
//    str += 'margin:%;';
//    str += 'margin-bottom:1px;';
    str += ' "'; 
    return str;
}

*/