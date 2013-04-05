


function create_constellation(div_name, configuration, constellation, username, gmt)
{
    var constellation_div = insert_constellation_div(div_name, configuration, constellation, username, gmt);
    
    var machines_div =  constellation_div.querySelector("#machines" );
    
    if(configuration == "cloudsim")
    {
        var machine_name = "cloudsim";
        var machine_div = create_machine(machines_div, machine_name);

        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file" );
        create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
        create_machine_state_widget(machine_div, constellation, machine_name, "simulation_aws_state", "simulation_state");
        // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");

        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file" );
        
        create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to CloudSim");


    }
    
    if (configuration == "vrc_constellation")
    {
        var machines =['router','field1', 'field2', 'sim'];
        
        create_task_list_widget(constellation_div, constellation);
        
        var mach_div =  constellation_div.querySelector("#machines" );
        for (var i=0; i < machines.length; i++)
        {
            var prefix = machines[i];
            var machine_name = prefix;
            var machine_div = create_machine(machines_div, machine_name);
            create_hostname_widget(machine_div, constellation, machine_name, prefix+"_ip_address", prefix+"_aws_id", "username", "gmt", prefix+"_zip_file");
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, prefix+"_launch_msg", prefix + "_state");
            create_machine_state_widget(machine_div, constellation, machine_name, prefix + "_aws_state", prefix + "_state");
            if(prefix == 'sim')
            {
                create_simulator_state_widget(machine_div, constellation, machine_name, prefix + "_glx_state", "gazebo");
            }
            create_latency_widget(machine_div, constellation, machine_name, prefix + "_latency", "RTT latency to CloudSim"); 
            
        }
    }

    if(configuration == "vpc_trio" || configuration == "vpc_micro_trio" || configuration == "vpc_trio_prerelease")
    {
    	create_task_list_widget(constellation_div, constellation);
    	// field computer
        { 
            var div =  constellation_div.querySelector("#machines" );
            

            var machine_name = "field_computer";
			var machine_div = create_machine(machines_div, machine_name);

            create_hostname_widget(machine_div, constellation, machine_name, "robot_ip", "robot_aws_id", "username", "gmt", "robot_zip_file");

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "robot_launch_msg", "robot_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "robot_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            
            create_latency_widget(machine_div, constellation, machine_name, "robot_latency", "RTT latency to the Router"); 
    	}
        // router computer
        {
            var machine_name = "router";
            var machine_div = create_machine(machines_div, machine_name);
            

            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "router_launch_msg", "router_state");
            create_machine_state_widget(machine_div,constellation, machine_name, "router_aws_state");
            //create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            create_hostname_widget(machine_div, constellation, machine_name, "router_public_ip", "router_aws_id", "username", "gmt", "router_zip_file");
            
            create_latency_widget(machine_div, constellation, machine_name, "router_latency", "RTT latency to the local computer"); 

        }
        
        // simulator computer
        {            
            var machine_name = "simulator";
            var machine_div = create_machine(machines_div, machine_name);
            
            create_hostname_widget (machine_div, constellation, machine_name, "sim_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file");	
            create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
            create_machine_state_widget(machine_div, constellation, machine_name,"simulation_aws_state");
            // create_machine_lifecycle_widget(machine_div,constellation, machine_name, "life_cycle");
            //create_glx_state_widget(machine_div, constellation, machine_name, "simulation_glx_state");
            
            create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");
            create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to the Router");
        }
        
    }
    
    if(configuration == "simulator" || configuration == "simulator_prerelease")
    {

        var machine_name = "simulator_" + constellation;

        create_task_list_widget(constellation_div, constellation);
        var machine_name = "simulator_" +constellation;

        var machine_div = create_machine(machines_div, machine_name);
        
        create_hostname_widget(machine_div, constellation, machine_name, "simulation_ip", "simulation_aws_id", "username", "gmt", "sim_zip_file" );	
        create_machine_launch_monitor_widget(machine_div, constellation, machine_name, "simulation_launch_msg", "simulation_state");
        create_machine_state_widget(machine_div, constellation, machine_name,"simulation_aws_state");
        //create_glx_state_widget(machine_div, constellation, machine_name, "simulation_glx_state");
        
        create_simulator_state_widget(machine_div, constellation, machine_name, "simulation_glx_state", "gazebo");

        //create_traffic_shaper_widget(machine_div, constellation, machine_name, "traffic_shaper");
        create_latency_widget(machine_div, constellation, machine_name, "simulation_latency", "RTT latency to the local computer");

    }
    
}



