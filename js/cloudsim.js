


function create_constellation(div_name, configuration, constellation, machine_data)
{
	
	var constellation_div = insert_constellation_div(div_name, configuration, constellation, username, machine_data.gmt);
   
    var machines_div =  constellation_div.querySelector("#machines" );
    
    if(configuration.indexOf ("OSRF VRC Constellation") == 0 || configuration.indexOf("AWS DRC") ==0)
    {
    	create_task_list_widget(constellation_div, constellation);
    	
    	for(var machine_name in machine_data.machines)
    	{
    		var has_simulator = false;
    		var latency_msg = "";
    		var disable_key_download  = false;
    		var latency_msg = "Latency between the router and " + machine_name;
    		
    		if (machine_name == "sim")
    		{
    			has_simulator = true;
    	    	if(get_user_info()['role'] == 'user')
    	    	{
    	    		disable_key_download = true;
    	    	}
    		}
    		else if (machine_name == "router")
    		{
    			latency_msg = "Latency between the router and the OCU over the VPN";
    		}
    		else
    		{
    			
    		}
    		
    		var machine_div = create_machine(machines_div, machine_name);
    		var ip_key = machine_name + "_ip";
    		var cloud_id_key = machine_name + "_aws_id";
    		var gmt_key = "gmt";
    		var zip_ready_key = machine_name + "_zip_file";
    		var username = machine_data.username;
    		create_hostname_widget (machine_div, constellation, machine_name, ip_key, cloud_id_key, username, gmt_key, zip_ready_key, disable_key_download);
    		
    		var launch_msg_key = machine_name + "_launch_msg";
    		var state_key = machine_name + "_state";
    		var latency_key = machine_name + "_latency";
    		create_machine_launch_monitor_widget(machine_div, constellation, machine_name, launch_msg_key, state_key);
    		
    		var cloud_state_key = machine_name + "_aws_state";
    		var machine_state_key = machine_name + "_state";
    		create_machine_state_widget(machine_div, constellation, machine_name, cloud_state_key, machine_state_key);
    		
    		if(has_simulator)
    		{
    			create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");
    		}
    		create_latency_widget(machine_div, constellation, machine_name, latency_key, latency_msg, 550);
    	}
    }
    	 
    if( (configuration == "AWS CloudSim") || (configuration.indexOf("OSRF CloudSim") ==0) )
    {
    	var disable_key_download  = false; 
    	if(get_user_info()['role'] == 'user')
    	{
    		disable_key_download = true;
    	}
    	var machine_name = "CloudSim";
        
        // create_task_list_widget(constellation_div, constellation);
        var machine_div = create_machine(machines_div, machine_name);
        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file", false );
        create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
        create_machine_state_widget(machine_div, constellation, machine_name, "simulation_aws_state", "simulation_state");
        // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");

        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file", false );
        create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to its parent CloudSim", 550);
    }

    
    if((configuration == "AWS simulator") || (configuration.indexOf("bitcoin") ==0))
    {
       
        create_task_list_widget(constellation_div, constellation);
        var machine_name = "simulator";
        var machine_div = create_machine(machines_div, machine_name);
        
        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file", disable_key_download );	
        create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
        create_machine_state_widget(machine_div, constellation, machine_name,"simulation_aws_state");
        //create_glx_state_widget(machine_div, constellation, machine_name, "simulation_glx_state");
        
        create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");

        //create_traffic_shaper_widget(machine_div, constellation, machine_name, "traffic_shaper");
        create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to CloudSim", 1.1);

    }
    
}



