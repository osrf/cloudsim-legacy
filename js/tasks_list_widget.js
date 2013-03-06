function create_tasks_list(div)
{
	var new_div = document.createElement("div");
    new_div.id = "task_list";    
    _set_mach_style(new_div.style);
    
    var str =  _get_machine_div_str("wazzu?");
    new_div.innerHTML = str;
    div.insertBefore(new_div, null);
    return new_div;	
}