
function create_hostname_widget(machine_div, 
                                constellation_name, 
                                machine_name,  
                                key_ip, 
                                key_aws_id, 
                                key_user, 
                                key_launch_date, 
                                key_zip_file)
{
	var table = machine_div.querySelector("table");
	var title = table.querySelectorAll("td");		
    
    $.subscribe("/constellation", function(event, msg){
        if(msg.constellation_name != constellation_name)
            return;
        
        // Remove the constellation name from the title
    	var machine_name_separator = machine_name.lastIndexOf("_")
    	var machine_name_only = machine_name.slice(0, machine_name_separator)
        
        title[0].innerHTML = "<td align='left'>" + machine_name_only + "</td>";
		title[1].innerHTML = "<td align='right'><FONT SIZE=2>IP: " + msg[key_ip] + "<FONT></td>";
		
		if (msg[key_zip_file] == 'ready')
		{
			var url = "/cloudsim/inside/cgi-bin/machine_zip_download.py?constellation=" + constellation_name + "&machine=" + machine_name;
			var str = "<td align='left'><form style='display: inline' action='" + url + "' method='post'><button>Download Keys</button></form></td>";
			//var str = "<td align='left'><a href='" + url + "'>Download Keys</a></form></td>";
			title[2].innerHTML = str;
		}
		title[3].innerHTML = "<td align='right'><FONT SIZE=2>AWS Id: " + msg[key_aws_id] + "<FONT></td>";			
    });
    
}
