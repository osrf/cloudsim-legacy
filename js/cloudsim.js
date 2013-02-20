


function create_constellation(div_name, configuration, constellation)
{
    var constellation_div = insert_constellation_div(div_name, configuration, constellation);
    
    if(configuration == "cloudsim")
    {
        var div =  constellation_div.querySelector("#machines" );
        var machine_name = "cloudsim_" + constellation
        var machine_div = create_machine(div, machine_name);

        create_machine_launch_monitor_widget(machine_div, constellation, machine_name,"launch_state", "simulation_launch");
        create_machine_state_widget(machine_div, constellation, machine_name, "cloud_state", "simulation_state");
        // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
        create_hostname_widget(machine_div, constellation, machine_name, "hostname", "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_key_ready" );
        create_latency_widget(machine_div, constellation, machine_name, "latency");
    }

    if(configuration == "vpc_trio" || configuration == "vpc_micro_trio" || configuration == "vpc_trio_prerelease" )
    {
    	// field computer
        { 
            var div =  constellation_div.querySelector("#machines" );
            
            var machine_name = "field_computer_" + constellation
            var machine_div = create_machine(div, machine_name);
            
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "launch_state" );
            create_machine_state_widget(machine_div,constellation, machine_name, "cloud_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget(machine_div, constellation, machine_name, "hostname");
            create_latency_widget(machine_div, constellation, machine_name, "latency"); 
    	}
        // router computer
        {
            var machine_name = "router_" + constellation
            var machine_div = create_machine(div, machine_name);
            
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name,"launch_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "cloud_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget(machine_div, constellation, machine_name, "hostname", "router_ip", "router_aws_id");
            create_traffic_shaper_widget(machine_div, constellation, machine_name, "traffic_shaper");
            create_latency_widget(machine_div, constellation, machine_name, "latency"); 
        }
        
        // simulator computer
        {
            var div =  constellation_div.querySelector("#machines" );
            var machine_name = "simulator_" + constellation;
            var machine_div = create_machine(div, machine_name);
            
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name,"launch_state");
            create_machine_state_widget(machine_div, constellation, machine_name,"cloud_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget (machine_div, constellation, machine_name, "hostname");	
            create_glx_state_widget(machine_div, constellation, machine_name, "glx_state");
            create_simulator_state_widget(machine_div, constellation, machine_name, "simulator_state");
            create_latency_widget(machine_div, constellation, machine_name, "latency");
        }
    }
    
    if(configuration == "simulator" || configuration == "simulator_prerelease")
    {
        var machine_name = "simulator_" +constellation;
    	
        var div =  constellation_div.querySelector("#machines" );
        var machine_div = create_machine(div, machine_name);
        
        create_machine_launch_monitor_widget(machine_div, constellation, machine_name,"launch_state");
        create_machine_state_widget(machine_div, constellation, machine_name,"cloud_state");
        create_hostname_widget (machine_div, constellation, machine_name, "hostname");	
        create_glx_state_widget(machine_div, constellation, machine_name, "glx_state");
        create_simulator_state_widget(machine_div, constellation, machine_name, "simulator_state");
        create_traffic_shaper_widget(machine_div, constellation, machine_name, "traffic_shaper");
        create_latency_widget(machine_div, constellation, machine_name, "latency");
    }
    
}



