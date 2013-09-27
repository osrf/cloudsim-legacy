

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

function create_machine(div, machine_name )
{
	
	var left = "";
	var right = "";

    console.log("create_machine_widget " + machine_name + " in div " + div.id);
    var widget = document.createElement("div");
    widget.className = "third_level_container";
    widget.id = machine_name;
    var title_div = document.createElement("div");
    widget.appendChild(title_div);
    title_div.className = "third_level_title";
    
    var title = '<table width="100%"><tbody><tr><td align="left">' + left +'</td>';
    title += '<td align="right">' + right + '</td></tr>';
    title += '<tr><td></td></tr>';
    title += '</tbody></table>';
    title_div.innerHTML = title;
    //var title = document.createTextNode(machine_name);
    //title_div.appendChild(title);
    
    var widgets_div = document.createElement("div");
    widgets_div.id = "widgets";
    widget.appendChild(widgets_div);
    
    div.appendChild(widget);
    return widget;

}


function _create_empty_widget(machine_div, widget_name)
{
    var widget = document.createElement("div");
    widget.id = widget_name;
    var widgets_div = machine_div.querySelector("#widgets");
    widgets_div.insertBefore(widget, null);
    return widget;
}




