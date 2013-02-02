// Units: ms.
var INITIAL_MIN_LATENCY = 0;
var MAX_LATENCY = 1000; 

//Units: percentage
var MAX_PACKAGE_LOSS = 100; 
var INITIAL_MIN_PACKET_LOSS = 0;

function create_traffic_shaper_widget(machine_div, constellation_name, machine_name, widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);

    var min_latency_text = document.createElement('input');
    min_latency_text.setAttribute('type','number');
    min_latency_text.setAttribute('name','minLatency');
    min_latency_text.setAttribute('value', INITIAL_MIN_LATENCY);
    min_latency_text.setAttribute('min', 0); 
    min_latency_text.setAttribute('max', MAX_LATENCY); 
    
    var min_packet_loss_text = document.createElement('input');
    min_packet_loss_text.setAttribute('type','number');
    min_packet_loss_text.setAttribute('name','minPacketLoss');
    min_packet_loss_text.setAttribute('value', INITIAL_MIN_PACKET_LOSS); 
    min_packet_loss_text.setAttribute('min', 0); 
    min_packet_loss_text.setAttribute('max', MAX_PACKAGE_LOSS); 
  
    var update_button = document.createElement('input');
    update_button.setAttribute('type','button');
    update_button.setAttribute('name','update');
    update_button.setAttribute('value','Update');
    
	update_button.onclick = function()
    {               
        update_traffic_shaper(constellation_name, machine_name, min_latency_text.value, min_packet_loss_text.value);
    };
        
    var reset_button = document.createElement('input');
    reset_button.setAttribute('type','button');
    reset_button.setAttribute('name','reset');
    reset_button.setAttribute('value','Reset');

    reset_button.onclick = function()
    {
        update_traffic_shaper(constellation_name, machine_name, INITIAL_MIN_LATENCY, INITIAL_MIN_PACKET_LOSS);           
        min_latency_text.value = INITIAL_MIN_LATENCY;
        min_packet_loss_text.value = INITIAL_MIN_PACKET_LOSS;
    };
    
    widget_div.appendChild(document.createTextNode("Min latency (ms.): "));
    widget_div.appendChild(min_latency_text);
    widget_div.appendChild(document.createTextNode("Min packet loss (%): "));
    widget_div.appendChild(min_packet_loss_text);
    widget_div.appendChild(update_button);
    widget_div.appendChild(reset_button);  
}
