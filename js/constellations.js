

function add_constellations_widget(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    // $("#"+div_name).append("<h2>Constellations</h2>");
    var div = document.getElementById(div_name);
    div.innerHTML = "<h2>Constellations</h2>";
    
    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name)
        {
            console.log("CONS " + data.constellation_name);
        }
    });
}



function get_constellation_names(div_name)
{
    var constellations = [];
    // look at the children 'div' they are named after the
    // constellation
    var div = document.getElementById(div_name);
    var nodes = div.childNodes; // getElementsByTagName('div');
    for(var i=0; i<nodes.length; i++) {
        var node = nodes[i];
        var title = node.id;
        if(title != undefined)
        {
            constellations.push(title);
        }
    }
    return constellations;
}

function _get_constellation_div_str(constellation_name)
{
    var str = "";
    str += '<div id="top" style="width = 100%; float:left; border-top-left-radius:10px; border-top-right-radius:15px; background-color:#44497a; width:100%; float:left;" ">' // background-color:#FFA500;
    str +=    "<h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
    str +=    constellation_name + "</center></h3>";    
    str += '</div>' // top
    str += "<button>Terminate</button>";
    str += "<div id='machines' ";
    str += 'style="clear:left; width=100%"';
    str += '></div>'; // machines
    return str;
}

function find_or_create_constellation_div(div_name, constellation)
{
    var div = document.getElementById(div_name);
    var nodes = div.childNodes;
    var node = nodes[0];
    for(var i=0; i<nodes.length; i++) 
    {
        node = nodes[i];
        var constellation_iter = node.id;
        if(constellation_iter == undefined)
            continue;
        var cmp = constellation_iter.localeCompare(constellation);
        console.log(constellation_iter+ " comp " + constellation + " = " + cmp);
        if(cmp > 0)
            break;
    }
    
    var const_div = document.createElement("div");
    const_div.id = constellation;
    var style = _get_const_style();
    const_div.style = style;
    const_div.innerHTML = _get_constellation_div_str(constellation);
    div.insertBefore(const_div, node);
    return const_div;
}

function constellation_add(div_name, constellation_name)
{    
    var str = "<div id='" + constellation_name + "'";
    str += ' style="' + _get_const_style() + '"';
	str += "> ";
	
	str += _get_constellation_div_str(constellation_name);

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



function _get_const_style()
{
    var str = "";
    str += 'width:98%; float:left; border-radius: 15px;';
    str += ' border: 1px solid black;'; 
    str += 'margin:1%;';
    //str += 'margin-bottom:20px;';
    return str;
}
/*
 function _get_const_style()
{
    var str = "";
    str += ' style="width:98%; float:left; border-radius: 15px;';
    str += ' border: 1px solid black;'; 
    str += 'margin:1%;';
    //str += 'margin-bottom:20px;';
    str +=  '"';
    return str;
}

 */