
function machine_view_on_load_page(div_name)
{
   var machines_div = document.getElementById(div_name);
   
   var str = "<div id='machines'></div><h3>Log</h3><div id='machines_log_div'></div>";
   machines_div.innerHTML = str;
}

function machine_view_status_event(div_name, str_data)
{
    var data = eval( '(' + str_data + ')' );
    var machine_name = data['machine'];
    if (machine_name == undefined)
    {
        return;
    }          
  
//    if(data.type == "check")
//    {
//        log_to_div("log_div", "<b>event</b> " + str_data);
//    }
    
    var machines_div = document.getElementById(div_name);
    var machines_list_div =machines_div.getElementsByTagName("div")[0] 

    var machine_list_div = machines_div.childNodes['machines'];
    var machine_div = machine_list_div.childNodes[machine_name];
    if( machine_div == undefined)
    {
      machine_div = _add_machine_div(machine_list_div, machine_name);
    }
    
    _update_machine_view(machine_div, data);
     
}

function _terminate_machine(machine_name)
{
    var r=confirm("terminate " + machine_name + "?");
    if (r==false)
    {
        return;
    }
    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=terminate&machine=' + machine_name;
    log_to_div("log_div", url);
    msg = httpGet(url);
    log_to_div("log_div", "");
    log_to_div("log_div", msg);
}

function _start_simulator(machine_name)
{

    var package_name = prompt("Enter the package: ", "pr2_gazebo");
    var launch_file_name = prompt("Enter the launch file name: ", "empty_world.launch");
    var launch_args = prompt("Enter the launch file arguments (optional): ", "");
    

    var r=confirm("Start simulator on machine" + machine_name + "?");
    if (r==false)
    {
        return;
    }    

    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=start_simulator';
    url += '&machine=' + machine_name;
    url += '&package=' + package_name;
    url += '&launch_file_name=' + launch_file_name;

    if(launch_args)
    {
        url += '&launch_args=' +  launch_args;
    }

    log_to_div("log_div", url);
    msg = httpGet(url);
    log_to_div("log_div", "");
    log_to_div("log_div", msg);

}

function _stop_simulator(machine_name)
{
    var r=confirm("Stop simulator on machine " + machine_name + "?");
    if (r==false)
    {
        return;
    }    

    var url = '/cloudsim/inside/cgi-bin/cloudsim_cmd.py?command=stop_simulator&machine=' + machine_name;
    log_to_div("log_div", url);
    msg = httpGet(url);
    log_to_div("log_div", "");
    log_to_div("log_div", msg);

}

function _add_machine_div(machine_list_div, machine_name)
{
    var str = "<div id =" + machine_name + " style='border: 1px solid red; margin: 5px; padding: 5px; '> ";
    str +=  "<h3>name = " +machine_name + "</h3>";   
    str += "<div id='latency' ><div id='data'><h3>Latency:</h3></div></div>";
    str += "<div id='graphics' ><h3>Graphics:</h3></div>";

    str += "<div id='simulator'><div id='data'></div>";

    str += "<button id='start_sim_btn' ";
    str += "onclick =\"_start_simulator('" + machine_name + "')\">Start</button>";
    
    str += "<button id='stop_sim_btn' ";
    str += "onclick =\"_stop_simulator('" + machine_name + "')\">Stop</button>";

    
    str += "</div>";

    str += "<div id='cloud'><h3>Cloud:</h3></div>";
    str += "<div id='state'><h3>State:</h3></div>";
    str += '<div id="zip_link" style="visibility:hidden;"><a href="/cloudsim/inside/cgi-bin/machine_zip_download.py?machine=';
    str += machine_name;
    str += '">Download keys</a></div>';
    str += '<br>';
    str += '<button type="button" onclick="_terminate_machine(\'';
    str += machine_name;    
    str += '\')">Terminate</button>';
    str += "<div id='log'></div>";    
    str += "</div>";
    
    machine_list_div.innerHTML += str;
    var machine_div = machine_list_div.childNodes[machine_name];
    return machine_div;
}

function _update_machine_view(machine_div, data)
{
   if(data.status == "latency")
   {
        var latency_div = machine_div.childNodes["latency"].childNodes["data"];
        var str = "<h3>Latency:</h3>";
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
       var str = "<h3>Cloud:</h3>"; 
       if(data)
       {
            for (var key in data )
            {
                var value = data[key]; 
                str += "<b>" + key + "</b>: " + value + "<br>";
            }
            
            if(data.success == "terminated" || data.success == "does_not_exist")
            {
                // machine_div.style.visibility = "hidden";
                machine_div.style.display = 'none';
            }   
       }
       div.innerHTML = str;
   }

   if(data.status == "graphics")
   {
        var div = machine_div.childNodes["graphics"];
        var str = "<h3>graphics: " + data.success + "</h3>";
        for (var key in data )
        {
            var value = data[key]; 
            str += "<b>" + key + "</b>: " + value + "<br>";
        }
        div.innerHTML = str;
   }

    if(data.status == "simulator")
    {
        var sim_div = machine_div.childNodes["simulator"];
        var data_div = sim_div.childNodes["data"];

        // var start_sim_button = sim_div.childNodes["start_sim_btn"];
        // var stop_sim_button  = sim_div.childNodes["stop_sim_btn"];
        // if(data.success == true) toggle_button.textContent = "Stop";
   
        var str = "<h3>simulator: "+ data.success + "</h3>"; 
        for (var key in data )
        {
            var value = data[key]; 
            str += "<b>" + key + "</b>: " + value + "<br>";
        }
        data_div.innerHTML = str;   
    }
   
   if(data.state)
   {
        var div = machine_div.childNodes["state"];
        var str = "<h3>Machine state: " + data.state + "</h3>";
        // if(data.retries != undefined) str += "retries " + data['try'] + "<br>"; 
        for (var key in data )
        {
            var value = data[key]; 
            str += "<b>" + key + "</b>: " + value + "<br>";
        }
        div.innerHTML = str;  
   }

   if(data.state == "ssh_wait_for_ready")
   {    
        // we know the zip is done at this point
        if(data.file == "/tmp/startup_script_done")
        {
            var div = machine_div.childNodes["zip_link"];
        }
   }    


  
}


