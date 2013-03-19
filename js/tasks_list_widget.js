function create_task_list_widget(const_div, constellation_name)
{ 
    var tasks_div = create_section(const_div, "tasks", "Simulation tasks");
    
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        {
            var tasks = data.tasks;
            for (var i=0; i < tasks.length; i++ )
            {
                var task = tasks[i];
                var task_widget = tasks_div.querySelector("#" + task.task_id);
                if(task_widget)
                {
                    	
                }
                else
                {
                    add_task_widget(const_div, task.task_id, "red", "run #");
                }
            }
        }
    });    
    
}

function add_task_widget(const_div, task_id, color, task_title, task_data )
{
    //var const_div = document.getElementById(constellation_name);
    var tasks_div = const_div.querySelector("#tasks");

    var task_div = document.createElement("div");
    task_div.id = task_id;
    task_div.style.float = "left"
    task_div.style.width = "100%"
    tasks_div.appendChild(task_div);

    var state_widget = document.createElement('img');
    state_widget.src = "/js/images/red_status.png";
    state_widget.width='18';
    state_widget.style.marginTop = "2px"
    
    var x_button= document.createElement('input');
    x_button.setAttribute('type','button');
    x_button.setAttribute('value','X');    

    var start_button= document.createElement('input');
    start_button.setAttribute('type','button');
    start_button.setAttribute('value','Start');

//    var stop_button= document.createElement('input');
//    stop_button.setAttribute('type','button');
//    stop_button.setAttribute('value','Stop');

    var edit_button= document.createElement('input');
    edit_button.setAttribute('type','button');
    edit_button.setAttribute('value','...');

    x_button.onclick =  function()
    {
        alert("no way! " + task_id);
    };

    edit_button.onclick =  function()
    {
        
        $( "#task-view-form" ).dialog( "open" );
    };

//    stop_button.onclick =  function()
//    {
//        alert("stop");
//    };
    
    start_button.onclick =  function()
    {
        alert("start");
    };
    
    var task_buttons_div = document.createElement("div");
    task_buttons_div.style.cssFloat = "left";
    //task_buttons_div.style.width = "20%";
    task_buttons_div.id = "buttons";
    task_buttons_div.appendChild(start_button);

    // task_buttons_div.appendChild(stop_button);
    task_buttons_div.appendChild(edit_button);
    task_buttons_div.appendChild(x_button);
    
    
    var task_title_div = document.createElement("div");
    task_title_div.style.cssFloat = "left";
    //task_title_div.style.width = "77%";
    
    task_title_div.id = "task_title";
    task_title_div.innerHTML = task_title;
    task_title_div.style.marginTop="3px";
    task_title_div.style.backgroundColor = "#f1f1f2";
    
    var task_status_div = document.createElement("div");
    task_status_div.appendChild(state_widget);
    task_status_div.style.cssFloat = "left";
    //task_status_div.style.width = "3%";
    
    task_div.appendChild(task_status_div);
    task_div.appendChild(task_buttons_div);
    task_div.appendChild(task_title_div);
    
    

}