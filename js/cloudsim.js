
function create_constellation(div_name, configuration, constellation)
{
    var constellation_div = insert_constellation_div(div_name, constellation);
    
    if(configuration == "cloudsim") return create_cloudsim_constellation(constellation_div, constellation);
    if(configuration == "drc_sim_ami") return create_drc_sim_ami_constellation(constellation_div, constellation);
    if(configuration == "drc_sim_12") return create_drc_sim_12_constellation(constellation_div, constellation);
    if(configuration == "micro_vpn") return create_micro_vpn_constellation(constellation_div, constellation);
    if(configuration == "ros_fuerte") return create_ros_fuerte_constellation(constellation_div, constellation);
}

function _create_basic_machine(constellation_div, constellation_name, machine_name)
{

    var div =  constellation_div.querySelector("#machines" );
    var machine_div = create_machine(div, machine_name);
    
    create_machine_state_widget(machine_div,constellation_name, machine_name, "cloud_state");
    create_machine_lifecycle_widget(machine_div,constellation_name, machine_name, "life_cycle");
    create_hostname_widget(machine_div, constellation_name, machine_name, "hostname");	
    create_latency_widget(machine_div, constellation_name, machine_name, "latency");
    
}

function _create_simulator_machine(constellation_div, constellation_name, machine_name)
{
    var div =  constellation_div.querySelector("#machines" );
    var machine_div = create_machine(div, machine_name);
    
    create_machine_state_widget(machine_div, constellation_name, machine_name,"cloud_state");
    create_machine_lifecycle_widget(machine_div,constellation_name, machine_name, "life_cycle");
    create_hostname_widget (machine_div, constellation_name, machine_name, "hostname");	
    create_glx_state_widget(machine_div, constellation_name, machine_name, "glx_state");
    create_simulator_state_widget(machine_div, constellation_name, machine_name, "simulator_state");
    create_latency_widget(machine_div, constellation_name, machine_name, "latency");
}

function create_cloudsim_constellation(constellation_div, constellation_name)
{
	var machine_name = "clousdim_" +constellation_name;
    _create_basic_machine(constellation_div, constellation_name, machine_name );
}

function create_drc_sim_ami_constellation(constellation_div, constellation_name)
{
    var machine_name = "simulator_" +constellation_name;
    _create_simulator_machine(constellation_div, constellation_name, machine_name);
}

function create_drc_sim_12_constellation(constellation_div, constellation_name)
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

