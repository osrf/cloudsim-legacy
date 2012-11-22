

function constellations_on_load_page(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    $("#"+div_name).append("<h2>Constellations</h2>");
    
    
}

function _get_const_style()
{
	var str = "";
	str += ' style="width:100%; float:left; border-radius: 15px;';
	str += ' padding:10px;' ;// ' margin:10px;'; //  
	str += ' border: 1px solid black;"'; // margin-bottom:20px;
	return str;
}

function constellation_add(div_name, constellation_name)
{
	var str = "<div id='" + constellation_name + "'";
	str += _get_const_style();
	str += "> ";
	
	str += constellation_name;
	str += "</div> ";
	
    $("#"+div_name).append(str);
    
}

function constellation_remove(div_name, constellation_name)
{
    // alert('remove from [' + div_name +']');
	var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    div.removeChild(constellation);
    
}