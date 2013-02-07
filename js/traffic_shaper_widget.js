// Units: ms.
var INITIAL_PACKET_LATENCY = 0;
var MAX_PACKET_LATENCY = 500; 

//Units: percentage
var MAX_PACKET_LOSS = 40; 
var INITIAL_PACKET_LOSS = 0;

function create_traffic_shaper_widget(_machineDiv, _constellationName, _machineName, _widgetName)
{
    var widget_div = _create_empty_widget(_machineDiv, _widgetName);

    var targetPacketLatency_text = document.createElement('input');
    targetPacketLatency_text.setAttribute('type','number');
    targetPacketLatency_text.setAttribute('name','targetPacketLatency');
    targetPacketLatency_text.setAttribute('value', INITIAL_PACKET_LATENCY);
    targetPacketLatency_text.setAttribute('min', 0); 
    targetPacketLatency_text.setAttribute('max', MAX_PACKET_LATENCY); 
    
    var targetPacketLoss_text = document.createElement('input');
    targetPacketLoss_text.setAttribute('type','number');
    targetPacketLoss_text.setAttribute('name','targetPacketLoss');
    targetPacketLoss_text.setAttribute('value', INITIAL_PACKET_LOSS); 
    targetPacketLoss_text.setAttribute('min', 0); 
    targetPacketLoss_text.setAttribute('max', MAX_PACKET_LOSS); 
  
    var update_button = document.createElement('input');
    update_button.setAttribute('type','button');
    update_button.setAttribute('name','update');
    update_button.setAttribute('value','Update');
    
	update_button.onclick = function()
    {               
        update_traffic_shaper(_constellationName, _machineName, targetPacketLatency_text.value, targetPacketLoss_text.value);
    };
        
    var reset_button = document.createElement('input');
    reset_button.setAttribute('type','button');
    reset_button.setAttribute('name','reset');
    reset_button.setAttribute('value','Reset');

    reset_button.onclick = function()
    {
        update_traffic_shaper(_constellationName, _machineName, INITIAL_PACKET_LATENCY, INITIAL_PACKET_LOSS);           
        targetPacketLatency_text.value = INITIAL_PACKET_LATENCY;
        targetPacketLoss_text.value = INITIAL_PACKET_LOSS;
    };
    
    widget_div.appendChild(document.createTextNode("Target latency (ms.): "));
    widget_div.appendChild(targetPacketLatency_text);
    widget_div.appendChild(document.createTextNode("Target packet loss (%): "));
    widget_div.appendChild(targetPacketLoss_text);
    widget_div.appendChild(update_button);
    widget_div.appendChild(reset_button);  
}
