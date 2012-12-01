

function _update_simulator_widget(widget_div, package, launch_file, args)
{

    var status = status_img("gray");
    
    var str = "";
	str += status;
    str += "<button>Start</button>";
    str += "<button>Stop</button>";
    str += 'package<input type="text" name="package">' + package + '</input>' ;
    str += 'launch file<input type="text" name="launch_file">'+launch_file+ '</input>';
    str += 'arguments<input type="text" name="args">' + args + '</input>';
    
    widget_div.innerHTML = str;
    
}

function add_simulator_state_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
    var str = "<div id='" + widget_name + "'";
	str += _get_widget_style();
	str += ">";
	str += widget_name;

    
    str += "</div>";

    var div = document.getElementById(div_name);
    var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
    machine.innerHTML += str;
}

function add_glx_state_widget(div_name, constellation_name, machine_name, widget_type, widget_name)
{
    var str = "<div id='" + widget_name + "'";
    str += _get_widget_style();
    str += ">";
    str += widget_name;
    var status = status_img("gray");
    str += status;
    str += "GL and X not running";
    str += "</div>";

    var div = document.getElementById(div_name);
    var machine = machine_get_widget_div(div_name, constellation_name, machine_name);
    machine.innerHTML += str;
}

/*
function _start_simulator(machine_name)
{

    var package_name = prompt("Enter the package: ", "drc_robot_utils"); // pr2_gazebo
    var launch_file_name = prompt("Enter the launch file name: ", "drc_robot.launch"); //empty_world.launch
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
*/