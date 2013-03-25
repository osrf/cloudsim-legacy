function add_task_widget(constellation_name, task_id, color, task_title, task_data )
{
    var const_div = document.getElementById(constellation_name);
    var tasks_div = const_div.querySelector("#tasks");

    var task_div = document.createElement("div");
    task_div.id = "task";
    task_div.style.float = "left"
    task_div.style.width = "100%"
    tasks_div.appendChild(task_div);

    var x_button= document.createElement('input');
    x_button.setAttribute('type','button');
    x_button.setAttribute('value','X');    

    var start_button= document.createElement('input');
    start_button.setAttribute('type','button');
    start_button.setAttribute('value','Start');

    var stop_button= document.createElement('input');
    stop_button.setAttribute('type','button');
    stop_button.setAttribute('value','Stop');

    var edit_button= document.createElement('input');
    edit_button.setAttribute('type','button');
    edit_button.setAttribute('value','Edit');

    x_button.onclick =  function()
    {
        alert("no way! " + task_id);
    };

    edit_button.onclick =  function()
    {
        
        $( "#task-view-form" ).dialog( "open" );
    };

    
    stop_button.onclick =  function()
    {
        alert("stop");
    };
    
    start_button.onclick =  function()
    {
        alert("start");
    };
    
    var task_buttons_div = document.createElement("div");
    task_buttons_div.style.cssFloat = "right";
    task_buttons_div.style.width = "20%";
    task_buttons_div.id = "buttons";
    task_buttons_div.appendChild(start_button);
    task_buttons_div.appendChild(stop_button);
    task_buttons_div.appendChild(edit_button);
    task_buttons_div.appendChild(x_button);
    
    
    var task_title_div = document.createElement("div");
    task_title_div.style.cssFloat = "left";
    task_title_div.style.width = "80%";
    
    task_title_div.id = "task_title";
    task_title_div.innerHTML = task_title;
    task_title_div.style.backgroundColor = "#f1f1f2";
    
    
    task_div.appendChild(task_title_div);
    task_div.appendChild(task_buttons_div);
    // attach to page
    
    
}