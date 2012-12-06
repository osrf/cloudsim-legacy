
function create_machine_lifecycle_widget(machine_div, constellation_name, machine_name, widget_name)
{

    var str = "";
    str += "<button>Reboot</button>";
    str += "<button>Start</button>";
    str += "<button>Stop</button>";
    

    var widget_div = _create_empty_widget(machine_div, widget_name);
    widget_div.innerHTML = str;
    
    
}

