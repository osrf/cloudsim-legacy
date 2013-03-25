
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

function _create_task_form(form_id)
{
    var form_div = document.createElement("div");

    form_div.id = form_id;
	
    form_div.title = "Task properties";
    var task_title_input = document.createElement("input");
    task_title_input.size = "35";
    form_div.appendChild(document.createTextNode("Task title"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(task_title_input);
    
    form_div.appendChild(document.createElement("br"));
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
    form_div.appendChild(document.createTextNode("Maximum time (sec)"));
    form_div.appendChild(document.createElement("br"));
    timeout.value = "1800";
    form_div.appendChild(timeout);

    var launch_arguments = document.createElement("input");
    launch_arguments.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Arguments"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(launch_arguments);
    
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createElement("br"));
    section = document.createElement("b");
    section.appendChild(document.createTextNode("Network parameters"));
    form_div.appendChild(section);
    form_div.appendChild(document.createElement("br"));
    
    var latency = document.createElement("input");
    latency.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Minimum latency (ms, round trip)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(latency);
    
    var uplink_data_cap = document.createElement("input");
    uplink_data_cap.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Uplink cap (bits for each s of run time)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(uplink_data_cap);

    var downlink_data_cap = document.createElement("input");
    downlink_data_cap.size = "35";
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createTextNode("Downlink cap (bits for each s of run time)"));
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(downlink_data_cap);    

    ros_package.value = "atlas_utils";
    launch_file.value = "atlas.launch";
    timeout.value = "1800";
    launch_arguments.value ="";
    latency.value ="0";
    uplink_data_cap.value="1000000";
    downlink_data_cap.value="1000000";
    return form_div;

}


function create_task_list_widget(const_div, constellation_name)
{ 

    var dlg_options = {
            autoOpen: false,
            height: 580,
            width: 450,
            modal: true,
            buttons: {
               "Create": function() {
	               var dlg = document.querySelector( "#" + form_id);
	               var inputs = dlg.querySelectorAll("input");
	               var title = inputs[0].value;
	               var ros_package = inputs[1].value;
	               var launch = inputs[2].value;
	               var timeout = inputs[3].value; 
	               var args = inputs[4].value;
	               var latency = inputs[5].value;
	               var uplink_data_cap = inputs[6].value;
	               var downlink_data_cap = inputs[7].value;
	               
	               console.log("timeout is " + timeout);
	               create_task(constellation_name, title, 
	                       ros_package, launch, timeout,
	                       args, latency, uplink_data_cap,
	                       downlink_data_cap);
	               
	               $( this ).dialog( "close" );
                }
              },

            close: function() {
          	  console.log("create_task_list_widget close");
            }
    };

    

	var tasks_div = create_section(const_div, "tasks", "Simulation tasks");
    //
    // create a form for the content 
    //

    var add_task_button = document.createElement('input');
    add_task_button.setAttribute('type','button');
    add_task_button.setAttribute('value','Create task...');
    add_task_button.onclick =  function()
    {
    	
    	$( "#task-view-form" ).dialog( "open" );
    }
    
    var stop_current_task_button = document.createElement('input');
    stop_current_task_button.setAttribute('type','button');
    stop_current_task_button.setAttribute('value','Stop current task...');
    stop_current_task_button.onclick =  function()
    {
        console.log("STOP!")
        stop_task(constellation_name);
    }

    var widgets_div = tasks_div.querySelector("#widgets");
    var p = widgets_div.parentElement;
    p.insertBefore(add_task_button, widgets_div);
    p.insertBefore(stop_current_task_button, widgets_div);



    var form_id = "task-view-form";
    var form_div = _create_task_form(form_id);
    p.insertBefore(form_div, widgets_div);
    
    // this is necessary, otherwise the form does not form
    setTimeout(function(){ $( "#task-view-form" ).dialog(dlg_options );}, 0);

    var task_div_list = widgets_div.children;

    $.subscribe("/constellation", function(event, data){
            if(data.constellation_name != constellation_name)
                return;
            
            
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

function _set_state_widget(state_widget, task_state)
{
    state_widget.src = "/js/images/gray_status.png";

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
    
    //
    // create a form for the content 
    //
    
    var form_id = "form_" +task_id;
    var form_div = _create_task_form(form_id);

    task_div.appendChild(form_div);

    var dlg = document.querySelector( "#" + form_id);
    var inputs = dlg.querySelectorAll("input");
    var title_input = inputs[0];
    
     $( "#" + form_id ).dialog({
      autoOpen: false,
      height: 600,
      width: 500,
      modal: true,
      buttons: {
         "Update": function() {
         console.log("Update " + constellation_name + "/" + task_id);

         var title = inputs[0].value;
         var ros_package = inputs[1].value;
         var launch = inputs[2].value;
         var timeout = inputs[3].value; 
         var args = inputs[4].value;
         var latency = inputs[5].value;
         var uplink_data_cap = inputs[6].value;
         var downlink_data_cap = inputs[7].value;
         
         update_task(constellation_name, task_id,
                title, ros_package,launch, timeout, args, latency, 
                uplink_data_cap, downlink_data_cap); 
         
         $( this ).dialog( "close" );
          }
        },

      close: function() {
          console.log("gone");
      }
    });

    var state_widget = document.createElement('img');
    state_widget.src = "/js/images/gray_status.png";
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
    edit_button.setAttribute('value','View');


    edit_button.onclick =  function()
    {
        
        var dlg = document.querySelector( "#" + form_id);
        var inputs = dlg.querySelectorAll("input");
        var task_title_input = inputs[0];
        var ros_package = inputs[1];
        var launch_file = inputs[2];
        var launch_arguments = inputs[4];
        var timeout = inputs[3]; 
        var latency = inputs[5];
        var uplink_data_cap = inputs[6];
        var downlink_data_cap = inputs[7];
        
        task = read_task(constellation_name, task_id);
        task_title_input.value = task.task_title;
        ros_package.value = task.ros_package;
        launch_file.value = task.ros_launch;
        timeout.value = task.timeout;
        launch_arguments.value = task.ros_args;
        latency.value = task.latency;
        uplink_data_cap.value = task.uplink_data_cap;
        downlink_data_cap.value = task.downlink_data_cap;
        $("#" + form_id ).dialog( "open" );
    };

    action_button.onclick =  function()
    {
        task = read_task(constellation_name, task_id);
        var state =task.task_state; 
        console.log(state);
        if(state == 'ready')
        {
            // var r = confirm('Start task "' + task.task_title + '"?')
            start_task(constellation_name, task.task_id);
        }
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

    x_button.onclick =  function()
    {
        var title = task_title_div.innerHTML;
        var r=confirm('Delete task: "' + title + '"?'  );
        if (r==false)
        {
            return;
        }
        delete_task(constellation_name, task_id);
    };

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
    
    var cb = function(event, data)
    {
    	
        if(data.constellation_name != constellation_name)
            return;
        
        var tasks = data.tasks;
        var task = _find_task_data(task_id, tasks);
        if(task)
        {
            if(task.task_title != task_title_div.innerHTML)
            {
                console.log("title change " + task_id);
                console.log("task state " + task.state);
                task_title_div.innerHTML = task.task_title;
            }
            console.log('TASK _set_state_widget: ' + constellation_name + ': '+ task.task_state)
            _set_state_widget(state_widget, task.task_state);
            
        }
        else
        {
            // task does not exist anymore
            if(task_div)
            {
                widgets_div.removeChild(task_div);
                task_div = null;
                $.unsubscribe("/constellation", cb);
            }
            else
            {
            	console.log("double delete");
            }
        }
    };
    $.subscribe("/constellation", cb);
}


