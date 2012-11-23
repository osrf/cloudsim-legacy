

function constellations_on_load_page(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    $("#"+div_name).append("<h2>Constellations</h2>");
    
    
}



function constellation_add(div_name, constellation_name)
{    
    var str = "<div id='" + constellation_name + "'";
	str += _get_const_style();
	str += "> ";
	
	// str += "<h3>" + constellation_name + "</h3>";
	
	//str += "<div>"
    str += '<div id="top" style="width = 100%; float:left; border-top-left-radius:10px; border-top-right-radius:15px; background-color:#44497a; width:100%; float:left;" ">' // background-color:#FFA500;
	
	
	
    str +=    "<h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
    str +=    constellation_name + "</center></h3>";    

    str += '</div>' // top
    
    //str += '<div style="clear:left; width=100%">Terminate';
    //str += "</div> ";
    str += "<button>Terminate</button>";
	str += "<div id='machines' ";
	str += 'style="clear:left; width=100%"';
	str += '></div>';
	
	//str += "</div>";
    
    
	

	
	str += "</div> "; // constellation
	
	$("#"+div_name).append(str);
    
}

function constellation_remove(div_name, constellation_name)
{
    // alert('remove from [' + div_name +']');
	var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    div.removeChild(constellation);   
}

function constellation_get_machines_div(div_name, constellation_name)
{
	var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    var machines = constellation.querySelector("#machines" );
    return machines;
}