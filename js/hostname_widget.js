
function create_hostname_widget(machine_div, 
                                constellation_name, 
                                machine_name,  
                                key_ip, 
                                key_aws_id, 
                                key_user, 
                                key_launch_date, 
                                key_zip_file,
                                disable_key_download)
{
	var table = machine_div.querySelector("table");
	var title = table.querySelectorAll("td");		
    
    $.subscribe("/constellation", function(event, msg){
        if(msg.constellation_name != constellation_name)
            return;

        
        title[0].innerHTML = "<td align='left'>" + machine_name + "</td>";
        
        var ip = msg[key_ip];
        
        // do not replace the string if the ip is there
        var ip_str = title[1].innerHTML;
		if(ip_str.indexOf(ip) == -1)
		{
			var ip =  msg[key_ip];
			var txt = "<td align='right'><FONT SIZE=2>IP:"
			if(ip)
			{
				txt += " <a href='http://" +  ip + "' target='_blank'>";
				txt +=    "<font color='white'>" 
				txt +=       msg[key_ip];
				txt +=    "</font>";
				txt += "</a>";
			}
			else
			{
				txt += "N/A";
			}
			txt += "<FONT></td>";
			title[1].innerHTML = txt;
			
		}
		
		if (msg[key_zip_file] == 'ready')
		{
			if(!disable_key_download)
			{
				if (title[2].innerHTML.indexOf(constellation_name) == -1)
    			{
    				var url = "/cloudsim/inside/cgi-bin/machine_zip_download.py?constellation=" + constellation_name + "&machine=" + machine_name;
    				var str = "<td align='left'><form style='display: inline' action='" + url + "' method='post'>";
    				
    				str += "<button >Download Keys</button></form></td>";
    				title[2].innerHTML = str;
    			}
    		}
		}
		
		// title[3].innerHTML = "<td align='right'><FONT SIZE=2>AWS Id: " + msg[key_aws_id] + "<FONT></td>";			
    });
    
}
