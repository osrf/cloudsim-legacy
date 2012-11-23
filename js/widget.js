

function constellations_on_load_page(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    $("#"+div_name).append("<h2>Constellations</h2>");
    
    
}



function widget_add(div_name, constellation_name, machine_name, widget_name)
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

function widget_remove(div_name, constellation_name, machine_name, widget_name)
{
    // alert('remove from [' + div_name +']');
    var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
    var widget = get_widget_div(div_name, constellation_name, machine_name, widget_name);
    machine.removeChild(widget);
}

function get_widget_div(div_name, constellation_name, machine_name, widget_name)
{
	var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
	widget = machine.querySelector("#" + widget_name);
	return widget;
}


