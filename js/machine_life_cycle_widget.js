
function create_machine_lifecycle_widget(machine_div, constellation_name, machine_name, widget_name)
{
    var widget_div = _create_empty_widget(machine_div, widget_name);
    
//    var str = "";
//    str += "<button>Reboot</button>";
//    str += "<button>Start</button>";
//    str += "<button>Stop</button>";
//    widget_div.innerHTML = str;

    var reboot_btn= document.createElement('input');
    reboot_btn.setAttribute('type','button');
    reboot_btn.setAttribute('name','reboot');
    reboot_btn.setAttribute('value','Reboot');
    reboot_btn.disabled = true;
    
    reboot_btn.onclick =  function(){
        _reboot_machine(constellation_name, machine_name);
    };
    
    var start_btn= document.createElement('input');
    start_btn.setAttribute('type','button');
    start_btn.setAttribute('name','start');
    start_btn.setAttribute('value','Start');
    start_btn.disabled = true;
    
    start_btn.onclick =  function(){
        _start_machine(constellation_name, machine_name);
    };
    
    var stop_btn= document.createElement('input');
    stop_btn.setAttribute('type','button');
    stop_btn.setAttribute('name','stop');
    stop_btn.setAttribute('value','Stop');
    stop_btn.disabled = true;
    
    stop_btn.onclick =  function(){
        _stop_machine(constellation_name, machine_name);
    };
    
    widget_div.appendChild(reboot_btn);
    widget_div.appendChild(start_btn);
    widget_div.appendChild(stop_btn);
}


function _reboot_machine(constellation_name, machine_name)
{
    var r  = confirm("Are you sure?")
    if (r==false)
    {
        return;
    }
    terminate_constellation(constellation_name);
}

