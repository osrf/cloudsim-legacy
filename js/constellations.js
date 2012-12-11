

function create_constellations_widget(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    var div = document.getElementById(div_name);
    div.innerHTML = "<h2>Constellations</h2>";
    
    $.subscribe("/cloudsim", function(event, data){
        if(data.constellation_name)
        {
        	var constellation = data.constellation_name;
        	var configuration = data.constellation_config;
            // console.log("CONS " + data.constellation_name);
            var constellation_div =  div.querySelector("#"+constellation);
            if( constellation_div == null)
            {
                create_constellation(div_name, configuration, constellation);
            }
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

function _get_constellation_div_str(div_name, configuration_name, constellation_name)
{
    var str = "";
    str += '<div id="top" style="';
    str += 'width = 100%; float:left; border-top-left-radius:10px; border-top-right-radius:15px;';
    str += ' background-color:#44497a; ';
    str += ' width:100%; float:left;" ">' // #44497a
    str += " <h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
    str +=   constellation_name + " [" + configuration_name + "]</center></h3>";    
    str += ' </div>' // top
    str += "<button ";
    str += ' style="border-radius: 5px;" ';
    str += "onclick=\"_constellation_terminate('"+div_name+"', '"+constellation_name+"');\">Terminate</button>";
    str += "<div id='machines' ";
    str += 'style="clear:left; width=100%"';
    str += '></div>'; // machines
    return str;
}

function _constellation_terminate(div_name, constellation_name)
{
    var r = confirm("terminate " + constellation_name + "?");
    if (r==false)
    {
        return;
    }
    terminate_constellation(constellation_name);
}


function insert_constellation_div(div_name, configuration, constellation)
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
        var cmp = constellation_iter.localeCompare(constellation);
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
    const_div.id = constellation;
    _set_const_style(const_div.style);
    const_div.innerHTML = _get_constellation_div_str(div_name, configuration, constellation);
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
    style.backgroundColor = "#F1F1F2";
}


