
//
//  Example task
//
/*
task_title: Task 1
task_id: 1
uplink_data_cap: 29491200
downlink_data_cap: 943718400
latency: 500
local_start: 2013-06-14 8:00:00.0
local_stop: 2013-06-14 18:00:00.0
timeout: 1800
task_num: 1
task_tag: Drive
ros_package: atlas_utils
ros_launch: vrc_task_1.launch
*/


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

function _add_form_textinput(form_div, title, readonly)
{
    var input_field  = document.createElement("input");
    input_field.size = "35";
    
    var title_text = document.createTextNode(title);
    var title_line = document.createElement("i")
    
    title_line.appendChild(title_text);
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(title_line);
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(input_field);
    return input_field;
}

function _add_form_separator(form_div, title)
{
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createElement("br"));
    section = document.createElement("b");
    section.appendChild(document.createTextNode(title));
    form_div.appendChild(section);	
}

                             
function _create_task_form(form_id)
{
    var form_div = document.createElement("div");

    form_div.id = form_id;
	
    form_div.title = "Task properties";
    var task_title_input = _add_form_textinput(form_div, "Task title");
    
    _add_form_separator(form_div, "Simulation parameters");
    
    var ros_package =  _add_form_textinput(form_div, "ROS package" );
    var launch_file =  _add_form_textinput(form_div, "Launch file" );
    var timeout =  _add_form_textinput(form_div, "Maximum time (sec)" );
    var launch_arguments =  _add_form_textinput(form_div, "Arguments" );

    _add_form_separator(form_div, "Network parameters");
    
    var latency =  _add_form_textinput(form_div, "Minimum latency (ms, round trip)");
    var uplink_data_cap=  _add_form_textinput(form_div, "Uplink data cap (bits)");
    var downlink_data_cap = _add_form_textinput(form_div, "Downlink data cap (bits)");

    _add_form_separator(form_div, "VRC parameters");

    var local_start = _add_form_textinput(form_div, "Valid from (UTC)");
    var local_stop = _add_form_textinput(form_div, "Valid until (UTC)");
    var vrc_id = _add_form_textinput(form_div, "VRC task ID");
    var vrc_num = _add_form_textinput(form_div, "VRC task num");

    // default values
    ros_package.value = "atlas_utils";
    launch_file.value = "atlas.launch";
    timeout.value = "1800";
    launch_arguments.value = "";
    latency.value ="0";
    uplink_data_cap.value =   "100000000";
    downlink_data_cap.value = "100000000";
    
    local_start.value = 'Thu Jan 31 2013 16:00:00 GMT-0800 (PST)';
    local_stop.value  = 'Fri Jan 31 2014 16:00:00 GMT-0800 (PST)';
    
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
	               var local_start = inputs[8].value;
	               var local_stop = inputs[9].value;
	               var vrc_id = inputs[10].value;
	               var vrc_num = inputs[11].value;
	               
	               console.log("timeout is " + timeout);
	               create_task(constellation_name, 
	            		   	   title, 
	                           ros_package, 
	                           launch, 
	                           timeout,
	                           args, 
	                           latency, 
	                           uplink_data_cap,
	                           downlink_data_cap,
	                           local_start,
	                           local_stop,
	                           vrc_id,
	                           vrc_num);
	               
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

    var form_id = constellation_name + "-task-view-form";

    var add_task_button = document.createElement('input');
    add_task_button.setAttribute('type','button');
    add_task_button.setAttribute('value','Create task...');
    add_task_button.onclick =  function()
    {
    	
    	$( "#" + form_id ).dialog( "open" );
    }
    if(get_user_info().role == "user")
    {
    	add_task_button.style.display='none';
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



    var form_div = _create_task_form(form_id);
    p.insertBefore(form_div, widgets_div);
    
    // this is necessary, otherwise the form does not form
    setTimeout(function(){ $( "#" + form_id ).dialog(dlg_options );}, 0);

    var task_div_list = widgets_div.children;

    $.subscribe("/constellation", function(event, data){
            if(data.constellation_name != constellation_name)
                return;
            
            var disable_stop = true;
            if (data.constellation_state = "running")
            {
            	if (data.current_task != "")
            	{
            		disable_stop = false;
            	}
            }
            stop_current_task_button.disabled = disable_stop;
            
            
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


function _set_button_state(action_button, task_state)
{
    action_button.setAttribute();
}

// add a new task line and widgets. Also subscribes to changes
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
    
    var dlg_buttons = {
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
                var local_start = inputs[8].value;
                var local_stop = inputs[9].value;
                var vrc_id = inputs[10].value;
                var vrc_num = inputs[11].value;
                
                update_task(constellation_name, task_id,
                       title, ros_package,launch, timeout, args, latency, 
                       uplink_data_cap, downlink_data_cap,
                       local_start,
                       local_stop,
                       vrc_id,
                       vrc_num); 
                
                $( this ).dialog( "close" );
                 }
               }; 
    
    if(get_user_info().role == "user")
    {
    	dlg_buttons = {
                "Close": function() 
                	{
                    $( this ).dialog( "close" );
                     }
                   }; 
    	
    }
    
     $( "#" + form_id ).dialog({
      autoOpen: false,
      height: 600,
      width: 500,
      modal: true,
      buttons: dlg_buttons,

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
    if(get_user_info().role == "user")
    {
    	x_button.style.display = "none";
    }

    var action_button= document.createElement('input');
    action_button.setAttribute('type','button');
    action_button.setAttribute('value','Start');

    var edit_button= document.createElement('input');
    edit_button.setAttribute('type','button');
    edit_button.setAttribute('value','...');


    edit_button.onclick =  function()
    {
        
        var dlg = document.querySelector( "#" + form_id);
        var inputs = dlg.querySelectorAll("input");
        
        // disable editing for users
        if(get_user_info().role == "user")
        {
            for (var i=0; i< 12; i++)
            {
                inputs[i].readOnly = true;
            }
        }
        
        var task_title_input = inputs[0];
        var ros_package = inputs[1];
        var launch_file = inputs[2];
        var launch_arguments = inputs[4];
        var timeout = inputs[3]; 
        var latency = inputs[5];
        var uplink_data_cap = inputs[6];
        var downlink_data_cap = inputs[7];
        
        var local_start = inputs[8];
        var local_stop = inputs[9];
        var vrc_id = inputs[10];
        var vrc_num = inputs[11];
        
        task = read_task(constellation_name, task_id);
        if (task == "Unauthorized")
        {
        	alert("You do not have sufficient privileges for this operation");
        	return;
        }
        
        task_title_input.value = task.task_title;
        ros_package.value = task.ros_package;
        launch_file.value = task.ros_launch;
        timeout.value = task.timeout;
        launch_arguments.value = task.ros_args;
        latency.value = task.latency;
        uplink_data_cap.value = task.uplink_data_cap;
        downlink_data_cap.value = task.downlink_data_cap;
        
        local_start.value = task.local_start;
        local_stop.value = task.local_stop;
        vrc_id.value = task.vrc_id;
        vrc_num.value = task.vrc_num;
        
        $("#" + form_id ).dialog( "open" );
    };


    action_button.onclick =  function()
    {
        console.log('start task '+ task_id);
        var state = "ready";
        if(state == 'ready')
        {
            start_task(constellation_name, task_id);
            location.reload(true);
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
    
    var count = 0;
    var cb = function(event, data)
    {
    	
        if(data.constellation_name != constellation_name)
            return;

        var tasks = data.tasks;
        var task = _find_task_data(task_id, tasks);
        if(task)
        {
        	// create a string with the task title and score message
        	var task_display_msg = "<b>" + task.task_title + "</b>";
        	task_display_msg += " " + task.task_message;
        	
            if(task_display_msg != task_title_div.innerHTML)
            {
                task_title_div.innerHTML = task_display_msg;
            }

            //  console.log('TASK _set_state_widget: ' + constellation_name + ': '+ task.task_state)
            state_widget.src = "/js/images/gray_status.png";
            if (task.task_state == "running")
            {
            	colors =  ["/js/images/gray_status.png", "/js/images/blue_status.png"];
                
            	// starting up color
            	if(data.gazebo == "not running")
            	{
            		colors[1] =  "/js/images/yellow_status.png";	
            	}
            		
            	var color = colors[count % colors.length];
                state_widget.src = color;
                action_button.disabled=true;
                x_button.disabled=true;
                edit_button.disabled=false;
            }

            if (task.task_state == "ready")
            {
                state_widget.src = "/js/images/gray_status.png";
                if(get_user_info().role == "user")
                {
                	edit_button.disabled=true;
                }
                
                // constellation is ready
                if(data.constellation_state == "running")
                {
                	// no other task running
                	if(data.current_task == "")
                	{
                		action_button.disabled=false;
                	}
                	else
                	{
                		action_button.disabled=true;
                	}
                	
                }
            }

            if (task.task_state == "stopping")
            {
            	colors =  ["/js/images/gray_status.png", "/js/images/red_status.png"];
                var color = colors[count % colors.length];
                state_widget.src = color;
                action_button.disabled=true;
                x_button.disabled=true;

            }

            if (task.task_state == "stopped")
            {
                state_widget.src = "/js/images/red_status.png";
                action_button.disabled=true;
                if(get_user_info().role == "user")
                {
                	x_button.disabled=true;
                }
                else
                {
                	x_button.disabled=false;
                }
            }

            // _set_state_widget(state_widget, task.task_state, count);
            
            // the count is used to blink the status
            if (count == 100) 
                 count =0;
             else 
                 count ++;
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


