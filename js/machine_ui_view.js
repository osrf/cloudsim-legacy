
function machine_view_on_load_page(div_name)
{
   var machines_div = document.getElementById(div_name);
   var str = "<h2>Running machines</h2><div id='machines'></div>";
   machines_div.innerHTML = str;
}

function _refresh_plots(machines_list_div)
{
	
	for (var i=0; i < machines_list_div.childNodes.length; i++)
	{
		var machine_div = machines_list_div.childNodes[i];
		var machine_name = machine_div.id;
		var plot_div_name = _machine_name_to_plot_div_name(machine_name);
		var latency_plot_data = latency_data[machine_name]['plot_data']
		var plot_options = latency_data[machine_name]['plot_options']		                                              
		latency_data[machine_name]['plot'] = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);
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

    var machine_list_div = machines_div.childNodes['machines'];
    var machine_div = machine_list_div.childNodes[machine_name];
    if( machine_div == undefined)
    {
      machine_div = _add_machine_div(machine_list_div, machine_name);
    }
    
    _update_machine_view(machine_div, data);
//    if(data.status == "latency")
//    {
//    	_refresh_plots(machines_list_div);
//   }
}

function _status_color(div_name, color)
{
	div_element = document.getElementById(div_name);
    if(color == "blue")
        div_element.innerHTML = "<img width='18' src='/js/images/blue_status.png'></img>";
    else if(color == "green")
        div_element.innerHTML = "<img width='18' src='/js/images/green_status.png'></img>";
    else if(color == "orange")
        div_element.innerHTML = "<img width='18' src='/js/images/orange_status.png'></img>";
    else if(color == "red")
        div_element.innerHTML = "<img width='18' src='/js/images/red_status.png'></img>";
    else if(color == "yellow")
        div_element.innerHTML = "<img width='18' src='/js/images/yellow_status.png'></img>";
    else if(color == "gray")
        div_element.innerHTML = "<img width='18' src='/js/images/gray_status.png'></img>";
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

function _machine_name_to_plot_div_name(machine_name)
{
	var plot_div_name = 'plot_div_' + machine_name;
	return plot_div_name;
}
function _machine_name_to_cloud_div_name(machine_name)
{
	var plot_div_name = 'cloud_div_' + machine_name;
	return plot_div_name;	
}
function _machine_name_to_gfx_div_name(machine_name)
{
	var plot_div_name = 'gfx_div_' + machine_name;
	return plot_div_name;	
}
function _machine_name_to_sim_div_name(machine_name)
{
	var plot_div_name = 'sim_div_' + machine_name;
	return plot_div_name;	
}

function _machine_name_to_info_div_name(machine_name)
{
	var info_div_name = 'info_div_' + machine_name;
	return info_div_name;
}


function _add_machine_div(machine_list_div, machine_name)
{
	var plot_div_name = _machine_name_to_plot_div_name(machine_name);

    var str = "<div id =" + machine_name + " style='background-color:#EEEEEE; width:100%;float:left;  margin-top: 10px;'> "; // border: 1px solid blue;

    
    var cloud_stat_div_name =  _machine_name_to_cloud_div_name(machine_name);
    var sim_stat_div_name = _machine_name_to_sim_div_name(machine_name);
    var gfx_stat_div_name = _machine_name_to_gfx_div_name(machine_name);
    var info_div_name = _machine_name_to_info_div_name(machine_name);
    var link = '/cloudsim/inside/cgi-bin/machine_zip_download.py';
    
    
    str += '<div id="top" style="background-color:#44497a; width:100%; float:left;" ">' // background-color:#FFA500;
//    str += '	<div style="width:20%; float:left;">';
//    str += '		<form method="get" action=' + link +'>';
//    str += '        <input type="text" ';
//    str += 			' value="' + machine_name +'" >';
//    str += '		</input>'	
//    str += '		<button type="submit">Download keys</button></form>';
//    str += 		"</div>"
//    str += '	<div style="float:left;">';
    str += "		<h3 style='margin-bottom:0; margin-top:0; color:white'><center>";
    str += 			machine_name + "</center></h3>";    
//    str += 		"</div>";
    str += '</div>' // top
    
    str += '<div id="left" style="width:50%;float:left;">';
    
    str += '<div>';
    	
    str += '<div id=' + info_div_name+ '  style="width:100%; float:left;">' // background-color:#FFD700;
    str += '<br><br>    [Waiting for update]'
    str += '</div>' // info
    
    str += '<div id="zip_link" style="float:left;">';
    str += '<a href="/cloudsim/inside/cgi-bin/machine_zip_download.py?machine=';
    str += machine_name;
    str += '">Download keys</a>';
    str += '</div>'; 
    		
    str += '</div>';
    
    str += '</div>' // left
    
    
    	
    str += '<div id="right" style=" width:50%;float:left;">';  
    str += ' '
    
    str += '<div style="width:100%;float:left;">';
    str += '	<div style="width:40%;float:left;">Machine status</div>';
    str += '	<div style="width:30%;float:left;" id="' + cloud_stat_div_name + '"></div>';
    str += '	<div style="width:30%;float:left;">';
    str += '	<button type="button" onclick="_terminate_machine(\'';
    str += 		machine_name;    
    str += 		'\')">Terminate</button>';
    str += "	</div>"; // button
    str += "</div>";

    str += '<div style="width:100%;float:left;">';
    str += '	<div style="width:40%;float:left;">Graphics status</div>';
    str += '	<div style="width:60%;float:left;" id="' + gfx_stat_div_name + '"></div>';
    str += "</div>";
    
    str += '<div style="width:100%;float:left;">';
    str += '	<div style="width:40%;float:left;">Simulator status</div>';
    str += '	<div style="width:30%;float:left;" id="' + sim_stat_div_name + '"></div>';
    str += '	<div style="width:30%;float:left;">';
    str += 	"		<button id='start_sim_btn' ";
    str += 	"		onclick =\"_start_simulator('" + machine_name + "')\">Start</button>";
    str += 	"		<button id='stop_sim_btn' ";
    str += 	"		onclick =\"_stop_simulator('" + machine_name + "')\">Stop</button>";
    str += "	</div>";
    str += "</div>";
    
//    str += '<div style="width:100%;float:left;">'
//    
//      str += "</div>";

    
    
    str += '</div>'; // right
    
    //
    //  PLOT
    //
    str += '<div id="bottom" style="float:left; width:100%; background-color:#7a7c7e;">' // #FFA500
    str += '<b><center>Latency</center></b>'
    str += "<div id='" + plot_div_name + "' style='width:100%; height:150px;' ></div>";
    str += '</div>'
    
    str += "<div id='latency' style='display:none;'><div id='data'><h3>Latency:</h3></div></div>";
    str += "<div id='graphics' style='display:none;' ><h3>Graphics:</h3></div>";
    str += "<div id='simulator' style='display:none;'><div id='data'></div>";
    str += "</div>";

    //str += "<div id='cloud'><h3>Keys</h3></div>";
    //str += "<div id='state' ><h3>State:</h3></div>";

    str +='</div>';
    str += '<br>';

    str += "<div id='log'></div>";    
    str += "</div>";
    
    machine_list_div.innerHTML += str;

        
    _status_color(cloud_stat_div_name, "gray");
    _status_color(gfx_stat_div_name, "gray");
    _status_color(sim_stat_div_name, "gray");
    
    var machine_div = machine_list_div.childNodes[machine_name];
    var latency_plot_data = [   
                                { label:"min", color: min_color, data:[] }, 
                                { label:"max", color: max_color, data:[]}, 
                                { label:"average", color:avg_color, data:[]} 
                            ];


    var plot_options = {
       
    // yaxis: {
    //        min: 0,
            //max: 110
    //    },

        xaxis: { 
            // font: null,
            min: 0,
            max: 30,
            tickFormatter : function (v, xaxis) 
            { 
                //var v = (xaxis.max -v);   
                var str = v.toFixed(0) + " s"; 
                return  str;
            },
            transform: function (v) { return -v; },
            inverseTransform: function (v) { return -v; }
        },

        legend: {
            show: false
        } ,

        grid: {
            borderWidth: 1,
            minBorderMargin: 20,
            labelMargin: 10,
            backgroundColor: {
                colors: ["#fff", "#e4f4f4"]
            },
            hoverable: true,
            mouseActiveRadius: 50,
            margin: {
                top: 8,
                bottom: 20,
                left: 20
            },
            markings: function(axes) {
                var markings = [];
                var xaxis = axes.xaxis;
                for (var x = Math.floor(xaxis.min); x < xaxis.max; x += xaxis.tickSize * 2) {
                    markings.push({ xaxis: {from: x, to: x + xaxis.tickSize }, color: "rgba(232, 232, 255, 0.2)" });
                }
                return markings;
            }
           
        }
    };

    
    // var j_plot = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);

    latency_data[machine_name] = { 'plot_data': latency_plot_data,
                                   // 'plot' : j_plot,
                                   'plot_options' : plot_options };
    
    return machine_div;
}

function _update_machine_view(machine_div, data)
{

   var machine_name = data.machine;
   
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
        
        
        var t = Date.now() * 0.001;
        var latency_plot_data = latency_data[machine_name]['plot_data'];
        var plot_div_name = 'plot_div_' + machine_name;
        add_latency_sample(latency_plot_data, t, data.min, data.max, data.avg, data.mdev);
         
        var plot_options = latency_data[machine_name]['plot_options']
        document.getElementById(plot_div_name).innerHTML = "";
        latency_data[machine_name]['plot'] = $.plot($('#' + plot_div_name), latency_plot_data, plot_options);
        
        
        //plot.setData(latency_plot_data);
        //plot.setupGrid();
        // plot.draw();
        
        
//        var plot_div = machine_div.childNodes['latency_plot'];
//        var latency_plot_data = latency_data[machine_name]['plot_data'];
//        latency_data[machine_name]['plot'] = $.plot($(plot_div), latency_plot_data, plot_options);
        
   }
   
   if(data.status == "cloud")
   {
	   var status_div_name = _machine_name_to_cloud_div_name(machine_name);
	   if(data.success == "running")
	   {
		   _status_color(status_div_name, "blue");
	   } 
	   else if (data.success == "shutting-down") 
	   {
		   _status_color(status_div_name, "orange");
	   } 
	   else
	   {      
		   _status_color(status_div_name, "red");         
	   }

	   var info_div_name = _machine_name_to_info_div_name(machine_name);
	   var div = document.getElementById(info_div_name);
	   var str = ""; 

	   if(data)
	   {	
		   //str += "<br>";
		   for (var key in data )
		   {
			   var value = data[key]; 
			   if (key != "status" && key != "machine" && key != "hostname" && key != "type" && key != "success")
			   {
				   str += "<b>" + key + "</b>: " + value + "<br>";
			   }
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
        var status_div_name = _machine_name_to_gfx_div_name(machine_name);
        if(data.success)
        {
            _status_color(status_div_name, "blue");
        }   
        else
        {      
            _status_color(status_div_name, "red");         
        }

        var str = "<h3>graphics: " + data.success + "</h3>";
        var div = machine_div.childNodes["graphics"];
        for (var key in data ) { str += "<b>" + key + "</b>: " + data[key] + "<br>";}
        div.innerHTML = str;
   }

   if(data.status == "simulator")
   {
	   var status_div_name = _machine_name_to_sim_div_name(machine_name);
        if(data.success)
        {
            _status_color(status_div_name, "blue");
        }   
        else
        {      
            _status_color(status_div_name, "red");         
        }

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
        
        var status_div_name = _machine_name_to_cloud_div_name(machine_name);
        if(data.type == "retry")
        {   
            if(data['try'] % 2 ==0)
            {        
                _status_color(status_div_name, "yellow");            
            }
            else
            {
               _status_color(status_div_name, "orange"); 
            }
        }     
   }

}



