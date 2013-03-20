
function _find_task_data(task_id, tasks)
{
	for(var i=0; i < tasks.length; i++)
    {
        var task = tasks[i];
        var id = task.task_id;
        if (id == task_id)
        {
            return task;
        }
    }
    return null;
}


function _split_tasks(task_div_list, 
                      tasks, 
                      new_tasks,
                      divs_to_update,
                      tasks_to_update, 
                      divs_to_delete)
{
    for(var i=0; i < task_div_list.length; i++)
    {
        var task_div = task_div_list[i];
        var task_id  = task_div.id;
        
        var task = _find_task_data(tasks);
        if (!task)
        {
        	divs_to_delete.push(task_div);
        }
        else
        {
            divs_to_update(task_div);
            tasks_to_update.push(task);
           
        }
    }
    
    for(var i=0; i < 5; i++)
    {
        console.log(i);
    }
    
	
    for(var i=0; i < tasks.length; i++)
    {
        var task = tasks[i];
        var task_id = task.task_id;
        
        if(_find_task_data(task_id, tasks_to_update) == null)
        {
            new_tasks.push(task);
        }
    }
    
}


function create_task_list_widget(const_div, constellation_name)
{ 
    var tasks_div = create_section(const_div, "tasks", "Simulation tasks");

    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        {
            var task_div_list = tasks_div.querySelector("#widgets").children;
            var new_tasks = [];
            var tasks = data.tasks;
            var divs_to_update = [];
            var deleted_task_divs = [];
            var tasks_to_update = [];
            
            _split_tasks(task_div_list, tasks, new_tasks, divs_to_update,
                tasks_to_update, deleted_task_divs);
            // add new divs
            for (var i=0; i < new_tasks.length; i++ )
            {
            	var task = new_tasks[i];
                add_task_widget(const_div, constellation_name, task.task_id, "gray", task.task_title);
                
            }

            // update existing divs
            for(var i=0; i < tasks_to_update.length; i++ )
            {
            	var task = tasks_to_update[i];
                var task_title = task.task_title;
                var task_div = divs_to_update[i];
                var div_title = task_div.querySelector("#task_title");
                
            }

            // remove deleted divs
            for (var i=0; i < deleted_task_divs.length; i++)
            {
                var div = deleted_task_divs[i];
                tasks_div.removeChild(div);
            }
        }
    });
    
}


function _set_task_style(style)
{   
    style.border = "1px solid black";
    style.width = "98%";
    style.float = "left";
    style.borderRadius= "8px";
    style.margin = "2px";
    //style.margin = "1%";
    // style.backgroundColor = "#f1f1f2";
}

function add_task_widget(const_div, constellation_name, task_id, color, task_title, task_data )
{
    //var const_div = document.getElementById(constellation_name);
    var tasks_div = const_div.querySelector("#tasks");
    var widgets_div = tasks_div.querySelector("#widgets");
    
    var task_div = document.createElement("div");
    task_div.id = task_id;
    _set_task_style(task_div.style);
    //task_div.style.float = "left";
    //task_div.style.width = "100%";
    widgets_div.appendChild(task_div);

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
    	var r=confirm('Delete task: "' + task_title + '?'  );
        if (r==false)
        {
            return;
        }
        delete_task(constellation_name, task_id);
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
    task_buttons_div.style.cssFloat = "right";
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