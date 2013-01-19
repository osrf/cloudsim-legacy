
function create_constellation(div_name, configuration, constellation)
{
    var constellation_div = insert_constellation_div(div_name, configuration, constellation);
    
    if(configuration == "cloudsim") return create_cloudsim_constellation(constellation_div, constellation);
    if(configuration == "drc_sim_ami") return create_drc_sim_ami_constellation(constellation_div, constellation);
    if(configuration == "drc_sim_latest") return create_drc_sim_latest(constellation_div, constellation);
    if(configuration == "micro_vpn") return create_micro_vpn_constellation(constellation_div, constellation);
    if(configuration == "ros_fuerte") return create_ros_fuerte_constellation(constellation_div, constellation);

    if(configuration == "vpc_trio")
    {
        _create_basic_machine(constellation_div, constellation, "field_computer_" + constellation );
        _create_basic_machine(constellation_div, constellation, "router_" + constellation );
        _create_simulator_machine(constellation_div, constellation, "simulator_" + constellation );
    }

    
    if(configuration == "micro_sim")
    {
        _create_basic_machine(constellation_div, constellation, "simulator_" + constellation );
        return;
    }

    if(configuration == "micro_robot")
    {
        _create_basic_machine(constellation_div, constellation, "robot_" + constellation );
        return;
    }
    
    if(configuration == "micro_duo")
    {
        _create_basic_machine(constellation_div, constellation, "simulator_" + constellation );
        _create_basic_machine(constellation_div, constellation, "robot_" + constellation );
        return;
    }
    
    if(configuration == "micro_duo")
    {
        _create_basic_machine(constellation_div, constellation, "simulator_" + constellation );
        _create_basic_machine(constellation_div, constellation, "robot_" + constellation );
        // _create_basic_machine(constellation_div, constellation, "router_" + constellation );
        return;
    }
    
    if(configuration == "robot")
    {
        _create_basic_machine(constellation_div, constellation, "robot_" + constellation );
        return;
    }
    if(configuration == "robot_and_simulator")
    {
    	_create_simulator_machine(constellation_div, constellation, "simulator_" + constellation );
        _create_basic_machine(constellation_div, constellation, "robot_" + constellation );
        // _create_basic_machine(constellation_div, constellation, "router_" + constellation );
        return;
    }
}

function _create_basic_machine(constellation_div, constellation_name, machine_name)
{

    var div =  constellation_div.querySelector("#machines" );
    var machine_div = create_machine(div, machine_name);
    
    create_machine_launch_monitor_widget(machine_div, constellation_name, machine_name,"launch_state");
    create_machine_state_widget(machine_div,constellation_name, machine_name, "cloud_state");
    //create_machine_lifecycle_widget(machine_div,constellation_name, machine_name, "life_cycle");
    create_hostname_widget(machine_div, constellation_name, machine_name, "hostname");	
    create_latency_widget(machine_div, constellation_name, machine_name, "latency");
    
}

function _create_simulator_machine(constellation_div, constellation_name, machine_name)
{
    var div =  constellation_div.querySelector("#machines" );
    var machine_div = create_machine(div, machine_name);
    
    create_machine_launch_monitor_widget(machine_div, constellation_name, machine_name,"launch_state");
    create_machine_state_widget(machine_div, constellation_name, machine_name,"cloud_state");
    //create_machine_lifecycle_widget(machine_div,constellation_name, machine_name, "life_cycle");
    create_hostname_widget (machine_div, constellation_name, machine_name, "hostname");	
    create_glx_state_widget(machine_div, constellation_name, machine_name, "glx_state");
    create_simulator_state_widget(machine_div, constellation_name, machine_name, "simulator_state");
    create_latency_widget(machine_div, constellation_name, machine_name, "latency");
}

function create_cloudsim_constellation(constellation_div, constellation_name)
{
	var machine_name = "cloudsim_" +constellation_name;
    _create_basic_machine(constellation_div, constellation_name, machine_name );
}

function create_drc_sim_ami_constellation(constellation_div, constellation_name)
{
    var machine_name = "simulator_" +constellation_name;
    _create_simulator_machine(constellation_div, constellation_name, machine_name);
}

function create_drc_sim_latest(constellation_div, constellation_name)
{   
    var machine_name = "simulator_" +constellation_name;
    _create_simulator_machine(constellation_div, constellation_name, machine_name);
}

function create_micro_vpn_constellation(constellation_div, constellation_name)
{    
    var machine_name = "micro_" +constellation_name;
    _create_basic_machine(constellation_div, constellation_name,machine_name);
}

function create_ros_fuerte_constellation(constellation_div, constellation_name)
{
    var machine_name = "ros_" + constellation_name;
	_create_basic_machine(constellation_div, constellation_name, machine_name);
}

