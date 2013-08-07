


function create_constellation(div_name, configuration, constellation, machine_data)
{
	var disable_key_download  = false; 
	if(get_user_info()['role'] == 'user')
	{
		disable_key_download = true;
	}
	
	var constellation_div = insert_constellation_div(div_name, configuration, constellation, username, machine_data.gmt);
    
    var machines_div =  constellation_div.querySelector("#machines" );
    
    if(configuration.indexOf ("OSRF VRC Constellation") == 0 || configuration.indexOf("AWS DRC") ==0)
    {
    	create_task_list_widget(constellation_div, constellation);
    	
    	for(var machine_name in machine_data.machines)
    	{
    		var has_simulator = false;
    		if (machine_name == "sim")
    		{
    			has_simulator = true;
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
    		var latency_msg = "what is my latency?";
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

    // if(configuration.indexOf("AWS trio") ==0 || configuration.indexOf("AWS micro trio") ==0  )
    if (false)
    {
    	create_task_list_widget(constellation_div, constellation);
    	// field computer
        { 
            var div =  constellation_div.querySelector("#machines" );
            

            var machine_name = "field_computer_" + constellation;
			var machine_div = create_machine(machines_div, machine_name);

            create_hostname_widget(machine_div, constellation, machine_name, "robot_ip", "robot_aws_id", "username", "gmt", "robot_zip_file", false);

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "robot_launch_msg", "robot_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "robot_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            
            create_latency_widget(machine_div, constellation, machine_name, "robot_latency", "RTT latency to the Router", 1.1); 
    	}
        // router computer
        {
            var machine_name = "router_" + constellation;
            var machine_div = create_machine(machines_div, machine_name);
            

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "router_launch_msg", "router_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "router_aws_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget(machine_div, constellation, machine_name, "router_public_ip", "router_aws_id", "username", "gmt", "router_zip_file", false);
            
            create_latency_widget(machine_div, constellation, machine_name, "router_latency", "RTT latency to CloudSim", 1.1); 
        }
        
        // simulator computer
        {            
            var machine_name = "simulator_" + constellation;
            var machine_div = create_machine(machines_div, machine_name);
            
            create_hostname_widget (machine_div, constellation, machine_name, "sim_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file", disable_key_download);	
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
            create_machine_state_widget(machine_div, constellation, machine_name,"simulation_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            //create_glx_state_widget(machine_div, constellation, machine_name, "simulation_glx_state");
            
            create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");
            create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to the Router", 1.1);
        }
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



