
function _find_task_data(task_id, tasks)
{
    try
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
        
    }
    catch(e)
    {
        return null;
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
        
        var task = _find_task_data(task_id, tasks);
        if (!task)
        {
        	divs_to_delete.push(task_div);
        }
        else
        {
            divs_to_update.push(task_div);
            tasks_to_update.push(task);
           
        }
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
    var widgets_div = tasks_div.querySelector("#widgets");
    var task_div_list = widgets_div.children;
    
    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name != constellation_name)
            return;
        {
            
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
                add_task_widget(const_div, constellation_name, task.task_id, "not started", task.task_title);
                
            }

            // update existing divs
            for(var i=0; i < tasks_to_update.length; i++ )
            {
            	var task = tasks_to_update[i];
                var task_title = task.task_title;
                var task_div = divs_to_update[i];
                var title_div = task_div.querySelector("#task_title");
                var div_title = title_div.innerHTML;
                
                if(task_title != task_title)
                {
                    console.log("" + task_title + " != " + div_title);
                    title_div.innerHTML = task_title;
                }
            }

            // remove deleted divs
            for (var i=0; i < deleted_task_divs.length; i++)
            {
                var div = deleted_task_divs[i];
                widgets_div.removeChild(div);
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

function _image(task_state)
{
    
}

function _set_button_state(action_button, task_state)
{
    action_button.setAttribute();
}

function add_task_widget(const_div, constellation_name, task_id, state, task_title, task_data )
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
    
    var form_div = document.createElement("div");
    var form_id = "form_" +task_id;
    form_div.id = form_id;
    var str = "";
    
    /*
    str += '<div id="task-view-form" title="Task  properties">';
    str += 'Task name<br><input size="35" type="text" name="title"></input><br>';
    str += '<b>Simulation properties</b><br>';
    str += 'ROS Package<br><input size="35" type="text" name="package"></input><br>';
    str += 'Launch file<br><input size="35" type="text" name="launch"></input><br>';
    str += 'Arguments<br><input size="35" type="text" name="args"></input><br>';
    str += 'Timeout (min)<br><input size="35" type="text" name="timeout"></input><br>';
    str += '<b>Network properties</b><br>';
    str += 'Target latency (ms)<br><input size="35" type="text" name="latency"></input><br>';
    str += 'Maximum data (MB)<br><input size="35" type="text" name="max_data"></input><br>';
    str += '</div>';
    form_div.innerHTML = str;
    */
	
    form_div.title = "Task properties";

    var task_title_input = document.createElement("input");
    task_title_input.size = "35";
    form_div.appendChild(document.createTextNode("Task title"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(task_title_input);
    form_div.appendChild(document.createElement("br"));
    
    var section = document.createElement("b");
    section.appendChild(document.createTextNode("Simulation parameters"));
    form_div.appendChild(section);
    
    var ros_package = document.createElement("input");
    ros_package.size = "35";
    
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("ROS package"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(ros_package);
    
    var launch_file = document.createElement("input");
    launch_file.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Launch file"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(launch_file);

    var timeout = document.createElement("input");
    timeout.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Timeout (min)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(timeout);
    
    var launch_arguments = document.createElement("input");
    launch_arguments.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Arguments"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(launch_arguments);
    
    form_div.appendChild(document.createElement("br"));
    section = document.createElement("b");
    section.appendChild(document.createTextNode("Network parameters"));
    form_div.appendChild(section);
    form_div.appendChild(document.createElement("br"));
    
    var latency = document.createElement("input");
    latency.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Target round trip latency (ms)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(latency);
    
    var data_cap = document.createElement("input");
    data_cap.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Maximum data transfer (MB)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(data_cap);
    
    task_div.appendChild(form_div);
    
     $( "#" + form_id ).dialog({
      autoOpen: false,
      height: 580,
      width: 450,
      modal: true,
      buttons: {
         "Save": function() {
         var dlg = document.querySelector("#task-view-form");
         var inputs = dlg.querySelectorAll("input");
         
         var title = inputs[0].value;
         var ros_package = inputs[1].value;
         var launch = inputs[2].value;
         var args = inputs[3].value;
         var timeout = inputs[4].value; 
         var latency = inputs[5].value;
         var data_cap = inputs[6].value;
         

         $( this ).dialog( "close" );
          }
        },
        
//        "Delete" : function() {
//            alert("What the hell are you trying to do?");
//        },
        
      //  Cancel: function() {
      //    $( this ).dialog( "close" );
      //  }
      //	},
      close: function() {
       //    allFields.val( "" ).removeClass( "ui-state-error" );
    	  console.log("gone");
      }
    });



    var state_widget = document.createElement('img');
    state_widget.src = "/js/images/red_status.png";
    state_widget.width='18';
    state_widget.style.marginTop = "2px"
    
    var x_button= document.createElement('input');
    x_button.setAttribute('type','button');
    x_button.setAttribute('value','X');

    var action_button= document.createElement('input');
    action_button.setAttribute('type','button');
    action_button.setAttribute('value','Start');

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
        
        task = get_task(constellation_name, task_id);
        task_title_input.value = task.task_title;
        ros_package.value = task.ros_package;
        launch_file.value = task.ros_launch;
        timeout.value = task.timeout;
        launch_arguments.value = task.ros_args;
        latency.value = task.latency;
        data_cap.value = task.data_cap;
        $("#" + form_id ).dialog( "open" );
    };

//    stop_button.onclick =  function()
//    {
//        alert("stop");
//    };
    
    action_button.onclick =  function()
    {
        alert("start");
    };
    
    var task_buttons_div = document.createElement("div");
    task_buttons_div.style.cssFloat = "right";
    //task_buttons_div.style.width = "20%";
    task_buttons_div.id = "buttons";
    task_buttons_div.appendChild(action_button);

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


