

function machines_on_load_page()
{
    console.log("machines_on_load_page");
    
}

function get_machine_names(div_name, constellation)
{
	var div = document.getElementById(div_name);
	var constellation_div =  div.querySelector("#"+constellation);
    var machines_div = constellation_div.querySelector("#machines" ); 
    
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

function _get_machine_div_str(machine_name)
{
    var str = "";
    str += '<div id="top" style="width = 100%; float:left; border-top-left-radius:10px; border-top-right-radius:15px; background-color:#44497a; width:100%; float:left;" ">' // background-color:#FFA500;
    str +=    "<h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
    str +=    machine_name + "</center></h3>";    
    str += '</div>' // top
    str += '<div id="widgets"';
    str += _get_machine_widgets_style();
    str +='></div>'; // widgets
    return str;
}

function create_machine(div, machine_name)
{
	var new_div = document.createElement("div");
    new_div.id = machine_name;    
    _set_mach_style(new_div.style);
    
    var str =  _get_machine_div_str(machine_name);
    new_div.innerHTML = str;
    div.insertBefore(new_div, null);
    return new_div;	
}

/*
function machine_get_widget_div(div_name, constellation_name, machine_name)
{
    var machines_div = find_or_create_machine_div(div_name, constellation_name, machine_name);
    var widgets_div = machine_div.querySelector("#widgets");
    return widgets_div;
}
*/
function _set_mach_style(style)
{   
    style.border = "1px solid black";
    style.width = "98%";
    style.float = "left";
    style.borderRadius= "15px";
    style.margin = "1%";
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


function _set_widget_style(style)
{
     style.width = "100%";
     style.float = "left";
}

function _create_empty_widget(machine_div, widget_name)
{
    var widget = document.createElement("div");
    widget.id = widget_name;
    _set_widget_style(widget.style);
    
    var widgets_div = machine_div.querySelector("#widgets");
    widgets_div.insertBefore(widget, null);
    return widget;
}

///////////////////

function create_machine_lifecycle_widget(machine_div, constellation_name, machine_name, widget_name)
{

    var str = "";
    str += "<button>Reboot</button>";
    str += "<button>Start</button>";
    str += "<button>Stop</button>";
    // str += "</div>";

    var widget_div = _create_empty_widget(machine_div, widget_name);
    widget_div.innerHTML = str;
}




