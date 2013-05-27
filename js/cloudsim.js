


function create_constellation(div_name, configuration, constellation, username, gmt)
{
	var disable_key_download  = false; 
	if(get_user_info()['role'] == 'user')
	{
		disable_key_download = true;
	}
	
	var constellation_div = insert_constellation_div(div_name, configuration, constellation, username, gmt);
    
    var machines_div =  constellation_div.querySelector("#machines" );
    
    if(configuration.indexOf ("OSRF VRC Constellation") == 0 )
    {
    	create_task_list_widget(constellation_div, constellation);
    	// field computer 1
        { 
            var div =  constellation_div.querySelector("#machines" );
            var machine_name = "field_computer1";
            var machine_div = create_machine(machines_div, machine_name);
            create_hostname_widget(machine_div, constellation, machine_name, "fc1_ip", "fc1_aws_id", "username", "gmt", "fc1_zip_file", false);
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "fc1_launch_msg", "fc1_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "fc1_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");

            create_latency_widget(machine_div, constellation, machine_name, "fc1_latency", "RTT latency to the Router", 1.1); 
    	}
    	// field computer 2
        { 
            var div =  constellation_div.querySelector("#machines" );
            var machine_name = "field_computer2";
			var machine_div = create_machine(machines_div, machine_name);

            create_hostname_widget(machine_div, constellation, machine_name, "fc2_ip", "fc2_aws_id", "username", "gmt", "fc2_zip_file", false);

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "fc2_launch_msg", "fc2_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "fc2_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            
            create_latency_widget(machine_div, constellation, machine_name, "fc2_latency", "RTT latency to the Router", 1.1); 
    	}
        // router computer
        {
            var machine_name = "router";
            var machine_div = create_machine(machines_div, machine_name);
            

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "router_launch_msg", "router_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "router_aws_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget(machine_div, constellation, machine_name, "router_ip", "router_aws_id", "username", "gmt", "router_zip_file", false);
            
            create_latency_widget(machine_div, constellation, machine_name, "router_latency", "RTT latency to the OCU accross the VPN", 550); 
        }
        
        // simulator computer
        {            
            var machine_name = "simulator";
            var machine_div = create_machine(machines_div, machine_name);
            
            create_hostname_widget (machine_div, constellation, machine_name, "sim_ip", "sim_aws_id", "username", "gmt", "sim_zip_file", disable_key_download);	
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "sim_launch_msg", "sim_state");
            create_machine_state_widget(machine_div, constellation, machine_name,"sim_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            //create_glx_state_widget(machine_div, constellation, machine_name, "simulation_glx_state");
            
            create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");
            create_latency_widget(machine_div, constellation, machine_name, "sim_latency", "RTT latency to the Router", 1.1);
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
        create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to its parent CloudSim", 1.1);
    }

    if(configuration.indexOf("AWS trio") ==0 || configuration.indexOf("AWS micro trio") ==0  )
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
    
    if(configuration == "AWS simulator")
    {
        var machine_name = "simulator_" + constellation;
        create_task_list_widget(constellation_div, constellation);
        var machine_name = "simulator_" +constellation;
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



