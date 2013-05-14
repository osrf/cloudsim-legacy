
function create_constellations_widget(div_name)
{
    console.log("create_constellations_widget " + div_name);
    var div = document.getElementById(div_name);
    div.setAttribute("style","background-color: #a8a7a7;border:1px solid #535453;border-radius: 15px;-moz-border-radius: 15px;-webkit-border-radius: 15px;");
    
    //var str = "<h2>Constellations</h2>";
    //div.innerHTML = str;

    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name)
        {
            var constellation = data.constellation_name;
            var configuration = data.configuration;
            var username = data.username;
            var gmt = data.gmt
            //data.constellation_config;
            var constellation_div =  div.querySelector("#"+constellation);
            if( constellation_div == null)
            {
                create_constellation(div_name, configuration, constellation, username, gmt);
            }
        }
    });
}



function insert_constellation_div(div_name, configuration_name, constellation_name, username, gmt)
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
        var cmp = constellation_iter.localeCompare(constellation_name);
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
    const_div.id = constellation_name;
    _set_const_style(const_div.style);
    
    var top_div = document.createElement("div");
    
    top_div.id = "top";
    top_div.setAttribute("style","background-color: #3573c0; border-top-left-radius: 15px; -moz-border-radius-topleft: 15px;\
                         -webkit-border-top-left-radius: 15px; border-top-right-radius: 15px; -moz-border-radius-topright:  15px;\
                         -webkit-border-top-right-radius: 15px;color: #ffffff; font-family: sans-serif; font-size:16px; margin-top: 0; padding:6px 20px;\
                         background-image: linear-gradient(bottom, rgb(30,55,117) 16%, rgb(100,109,217) 87%);\
                         background-image: -o-linear-gradient(bottom, rgb(30,55,117) 16%, rgb(100,109,217) 87%);\
                         background-image: -moz-linear-gradient(bottom, rgb(30,55,117) 16%, rgb(100,109,217) 87%);\
                         background-image: -webkit-linear-gradient(bottom, rgb(30,55,117) 16%, rgb(100,109,217) 87%);\
                         background-image: -ms-linear-gradient(bottom, rgb(30,55,117) 16%, rgb(100,109,217) 87%);\
                         background-image: -webkit-gradient(linear, left bottom, left top, color-stop(0.16, rgb(30,55,117)), color-stop(0.87, rgb(100,109,217)));");
  
    var title_str = "<div><span>Constellation: <b>" + constellation_name + "</b></span>";
    title_str    += "<span style='float: right;'>Launched By: <b>" + username + "</b></span></div>";
    title_str    += "<div><span>Configuration: " + configuration_name + "</span>";
    title_str    += "<span style='float: right;'>Launch Datetime: " + gmt + "</span></div>";
    
    top_div.innerHTML = title_str;
    
    const_div.appendChild(top_div);
    
    // div.insertBefore(top_div, node);


    var msg_div = document.createElement("div");
    msg_div.id = "error";
    msg_div.style.color = "red"; 
    const_div.appendChild(msg_div);

    var terminate_button= document.createElement('input');
    terminate_button.setAttribute('type','button');
    terminate_button.setAttribute('value','Terminate');
    terminate_button.setAttribute('style','margin-top:4px; background: #f4f4f4; color: #000; padding:2px 6px;\
                                  cursor: pointer; border-radius: 4px; -moz-border-radius: 4px; -webkit-border-radius: 4px;');

    terminate_button.onclick =  function()
    {   
        var r = confirm("terminate " + constellation_name + "?");
        if (r==false)
        {
            return;
        }
        terminate_constellation(constellation_name);
    };
    
    top_div.appendChild(terminate_button);



    //create_task_list_widget(const_div, constellation_name);
//    var tasks_div = document.createElement("div");
//    tasks_div.id = "tasks";
//    const_div.appendChild(tasks_div);
    
    var machines_div = document.createElement("div");
    machines_div.id = "machines";
    const_div.appendChild(machines_div);
     

    // const_div.innerHTML = _get_constellation_div_str(div_name, configuration, constellation);
    div.insertBefore(const_div, node);
    
    return const_div;
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


function constellation_remove(div_name, constellation_name)
{
    var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    div.removeChild(constellation);   
}


function _set_const_style(style)
{
    style.width = "98%";
    style.border="1px solid #535453";
    style.borderRadius = "15px";
    style.margin = "1%";
    style.backgroundColor = "#cccccc"; // f1f1f2
    style.overflow = "hidden";
}


