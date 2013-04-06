// Units: ms.
var INITIAL_PACKET_LATENCY = 0;
var MAX_PACKET_LATENCY = 500; 

function create_traffic_shaper_widget(_machineDiv, _constellationName, _machineName, _widgetName)
{
    var widget_div = _create_empty_widget(_machineDiv, _widgetName);
    widget_div.setAttribute("style", "width: 100%; float: left; height: 10px; padding: 0px 0px 10px 17px; position: relative;");


    var targetPacketLatency_text = document.createElement('input');
    targetPacketLatency_text.setAttribute('type','number');
    targetPacketLatency_text.setAttribute('name','targetPacketLatency');
    targetPacketLatency_text.setAttribute('value', INITIAL_PACKET_LATENCY);
    targetPacketLatency_text.setAttribute('min', 0); 
    targetPacketLatency_text.setAttribute('max', MAX_PACKET_LATENCY);
  
    var update_button = document.createElement('input');
    update_button.setAttribute('type','button');
    update_button.setAttribute('name','update');
    update_button.setAttribute('value','Update');
    
	update_button.onclick = function()
    {               
        update_traffic_shaper(_constellationName, _machineName, targetPacketLatency_text.value);
    };
        
    var reset_button = document.createElement('input');
    reset_button.setAttribute('type','button');
    reset_button.setAttribute('name','reset');
    reset_button.setAttribute('value','Reset');

    reset_button.onclick = function()
    {
        update_traffic_shaper(_constellationName, _machineName, INITIAL_PACKET_LATENCY);           
        targetPacketLatency_text.value = INITIAL_PACKET_LATENCY;
    };
    
    widget_div.appendChild(document.createTextNode("Target latency (ms.): "));
    widget_div.appendChild(targetPacketLatency_text);
    widget_div.appendChild(update_button);
    widget_div.appendChild(reset_button);  
}
