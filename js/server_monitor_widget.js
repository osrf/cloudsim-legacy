
function create_server_monitor_widget(div_name)
{
    var div = document.querySelector("#"+div_name);
    
    
    var widget_div = document.createElement("div");
    widget_div.id = "inner";
    _set_widget_style(widget_div.style);
    
    
    var status_div = document.createElement("div");	
    status_div.innerHTML = status_img("gray");
    
    
    var log_div = document.createElement("div");
    
    div.appendChild(widget_div);
    widget_div.appendChild(status_div);
    widget_div.appendChild(log_div);
    
    
    
    
    
    var count = 0;
    
    $.subscribe("/cloudsim", function(event, data){
       
       if(!data.type)
    	   return;
       
       var str = "<br><b><i> --- " + data.type + " --- </b></i><br>";
       for (var key in data )
       {
           if (key == "type") continue;
           
    	   var value = data[key]; 
           str += "<b>   " + key + "</b>: " + value + "<br>";
       }
       
       //log_div.innerHTML += str;
       	
       var msg = data.type;
       var colors = ["gray", "yellow", "orange", "blue", "green"];
       count ++;
       if(count >= colors.length)
       {
           count =0;
       }
       var color = colors[count];
       status_div.innerHTML =  status_img(color); // + " " + msg;

    });
}
