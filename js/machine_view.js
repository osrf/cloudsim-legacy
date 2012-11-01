
function machine_view_on_load_page(div_name)
{
   var machines_div = document.getElementById(div_name);
   
   var str = "<div id='machines'></div><h3>Log</h3><div id='machines_log_div'></div>";
   machines_div.innerHTML = str;
}


function _add_machine_div(machine_list_div, machine_name)
{
    var str = "<div id =" + machine_name + " style='border: 1px solid red;'> ";
    str +=  "<h3>name = " +machine_name + "</h3>";   
    str += "<div id='latency' ></div>";
    str += "<div id='graphics' ></div>";
    str += "<div id='simulator'></div>";
    str += "<div id='cloud'></div>";
    str += "<div id='state'></div>";
    str += '<a href="/cloudsim/inside/cgi-bin/download_machine_keys.py?machine_id=';
    str += machine_name;
    str += '5&amp;action=terminate">Download keys</a>';
    str += '<br>';
    str += '<button type="button" onclick="alert(\'Not yet\')">Terminate</button>';
    str += "</div>";
    machine_list_div.innerHTML += str;
    var machine_div = machine_list_div.childNodes[machine_name];
    return machine_div;
}

function _update_machine_view(machine_div, data)
{
   if(data.status == "latency")
   {
        var latency_div = machine_div.childNodes["latency"];
        var str = "<h3>Latency</h3>";
        str += "<b>count:</b> " + data.count + "<br>";  
        str += "<b>min:</b> " + data.min + "<br>";
        str += "<b>max:</b> " + data.max + "<br>";
        str += "<b>avg:</b> " + data.avg + "<br>";
        str += "<b>mdev:</b> " + data.mdev + "<br>";
        latency_div.innerHTML = str;
   }
   
   if(data.status == "cloud")
   {
       var div = machine_div.childNodes["cloud"];
       var str = "<h3>Cloud: " + data.success + "</h3>"; 
       div.innerHTML = str;
   }

   if(data.status == "graphics")
   {
       var div = machine_div.childNodes["graphics"];
       var str = "<h3>graphics: " + data.success + "</h3>";
       div.innerHTML = str;
   }

   if(data.status == "simulator")
   {
       var div = machine_div.childNodes["simulator"];
       var str = "<h3>simulator: "+ data.success + "</h3>"; 
       div.innerHTML = str;   
   }
   
   if(data.state != undefined)
   {
     var div = machine_div.childNodes["state"];
     var str = "<h3>Machine state: " + data.state + "</h3>";
     if(data.retries != undefined) str += "retries " + data['try'] + "<br>"; 
     div.innerHTML = str;  
   }

}

function machine_view_status_event(div_name, str_data)
{
    var data = eval( '(' + str_data + ')' );
    var machine_name = data['machine'];
    if (machine_name == undefined)
    {
        return;
    }          
  
    var machines_div = document.getElementById(div_name);
    var machines_list_div =machines_div.getElementsByTagName("div")[0] 

    // log_to_div("machines_log_div", "<b>event</b> " + str_data);
    
    var machine_list_div = machines_div.childNodes['machines'];
    var machine_div = machine_list_div.childNodes[machine_name];
    if( machine_div == undefined)
    {
      machine_div = _add_machine_div(machine_list_div, machine_name);
    }
    
    _update_machine_view(machine_div, data);
     
}
