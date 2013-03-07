
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
    
    $.subscribe("/constellation", function(event, data){
       
       	
       var colors = ["gray", "blue"];
       count ++;
       if(count >= colors.length)
       {
           count =0;
       }
       var color = colors[count];
       status_div.innerHTML =  status_img(color);

    });
}
