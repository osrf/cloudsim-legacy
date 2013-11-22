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

function _add_form_textinput(form_div, title, visible)
{
    var input_field  = document.createElement("input");
    input_field.size = "35";
    
    var title_text = document.createTextNode(title);
    var title_line = document.createElement("i")
    
    title_line.appendChild(title_text);
    if(visible)
    	form_div.appendChild(document.createElement("br"));
    form_div.appendChild(title_line);
    if(visible)
    	form_div.appendChild(document.createElement("br"));
    form_div.appendChild(input_field);

    if(visible == false)
    {
    	input_field.style.display = "none";
    	title_line.style.display  = "none";
    }    
    return input_field;
}

function _create_task_form(form_id)
{
    var form_div = document.createElement("div");
    form_div.id = form_id;
    form_div.title = "Task dialog";
    
    var title_input = document.createElement("input");
    title_input.size = 35;
    form_div.appendChild(document.createElement("br"));
    
    form_div.appendChild(document.createTextNode("Task title"));
    form_div.appendChild(title_input);
    form_div.appendChild(document.createElement("br"));
    form_div.appendChild(document.createElement("br"));
    
    var tabs_div = document.createElement('div');
    tabs_div.id = "tabs_" + form_id;
    var t = '<ul>';
    t += '<li><a href="#tab-sim">Simulation</a></li>';
    t += '<li><a href="#tab-network">Networking</a></li>';
    t += '<li><a href="#tab-calendar">Availability</a></li>';
    t += '</ul>';
    tabs_div.innerHTML = t;
    form_div.appendChild(tabs_div);
    
    var visible = true;
    var tab1 = document.createElement("div");
    tab1.id = 'tab-sim';
    var ros_package =  _add_form_textinput(tab1, "ROS package", visible);
    var launch_file =  _add_form_textinput(tab1, "Launch file", visible);
    var timeout =  _add_form_textinput(tab1, "Maximum time (sec)", visible);
    var launch_arguments =  _add_form_textinput(tab1, "Arguments", visible );
    tabs_div.appendChild(tab1)

    var tab2 = document.createElement("div");
    tab2.id = 'tab-network';
    var latency =  _add_form_textinput(tab2, "Minimum latency (ms, round trip)", visible);
    var uplink_data_cap=  _add_form_textinput(tab2, "Uplink data cap (bits, 0 for unlimited)", visible);
    var downlink_data_cap = _add_form_textinput(tab2, "Downlink data cap (bits, 0 for unlimited)", visible)
    tabs_div.appendChild(tab2)

    var tab3 = document.createElement("div");
    tab3.id = 'tab-calendar';
    var local_start = _add_form_textinput(tab3, "Valid from (UTC)", visible);
    var local_stop = _add_form_textinput(tab3, "Valid until (UTC)", visible);
    visible = false;
    var vrc_id = _add_form_textinput(form_div, "Run (1, 2, 3, 4 or 5)", visible);
    var vrc_num = _add_form_textinput(form_div, "Task (1, 2 or 3)", visible);   	
    tabs_div.appendChild(tab3)   

    // Default values
    ros_package.value = "drcsim_gazebo";
    launch_file.value = "vrc_task_1.launch";
    timeout.value = "1800";
    launch_arguments.value = "";
    latency.value ="0";
    uplink_data_cap.value =   "0";
    downlink_data_cap.value = "0";
    vrc_id.value = "1";
    vrc_num.value = "1";

    local_start.value = '2013-01-01T00:00:00.0';
    local_stop.value  = '2014-01-01T00:00:00.0';

    return form_div;  
}

function create_task_list_widget(const_div, constellation_name)
{ 
    // create a form for the content 
    var form_id = constellation_name + "-task-view-form";
    
    var dlg_options = {
            autoOpen: false,
            height: 550,
            width: 500,
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
	               
	               console.log( "create_task_list_widget #" + form_id);
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
          	  console.log("create_task_list_widget close #" + form_id);
            },
            
            open: function() { 
            	console.log("create_task_list_widget open #" + form_id);
            	$("#tabs_" + form_id).tabs();

            }
    };


	var tasks_div = document.createElement("div");
	tasks_div.id = "tasks";
	tasks_div.className = "third_level_container";


	var title_div = document.createElement("div");
	title_div.className = "third_level_title";
	tasks_div.appendChild(title_div);
	
	var title = document.createTextNode("Simulation tasks")
	title_div.appendChild(title);
	
	var widgets_div =  document.createElement("div");
	widgets_div.id = "widgets";
	tasks_div.appendChild(widgets_div);
	
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
        console.log("onclick stop_current_task_button!")
        stop_task(constellation_name);
        page_refresh();
    }
    
    var reset_tasks_button = document.createElement('input');
    reset_tasks_button.setAttribute('type','button');
    reset_tasks_button.setAttribute('value','Reset tasks');
    reset_tasks_button.onclick = function()
    {
    	var txt  = "This clear the current task and will make all finished tasks ready to run again.";
    	txt += "\n";
    	txt += "This operation will not stop the simulator if its currently running.";
    	txt += "\n\n";
    	txt += 'Are you sure?';
    	var r=confirm(txt);
        if (r==false)
        {
            return;
        }
    	console.log("onclick reset_tasks_button!")
    	reset_tasks(constellation_name);
    }
    if(get_user_info().role == "user")
    {
    	reset_tasks_button.style.display='none';
    }
    
    // Add the buttons
    var widgets_div = tasks_div.querySelector("#widgets");
    var p = widgets_div.parentElement;
    var buttons_div = document.createElement("div");
    buttons_div.setAttribute("align", "right");
    p.insertBefore(buttons_div, widgets_div);
    buttons_div.appendChild(add_task_button);
    buttons_div.appendChild(stop_current_task_button);
    buttons_div.appendChild(reset_tasks_button);

    var form_div = _create_task_form(form_id);	
    p.insertBefore(form_div, widgets_div);

    // this is necessary, otherwise the form does not form
    setTimeout(function()
    	{ 	
    		$( "#" + form_id ).dialog(dlg_options );
    	}, 0);

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
    var top_div = const_div.querySelector("#top");
    top_div.appendChild(tasks_div);
}

function _set_button_state(action_button, task_state)
{
    action_button.setAttribute();
}

// Add a new task line and widgets. Also subscribes to changes
function add_task_widget(const_div, constellation_name, task_id, state, task_title, task_data )
{
    // var const_div = document.getElementById(constellation_name);
    var tasks_div = const_div.querySelector("#tasks");
    
    var widgets_div = tasks_div.querySelector("#widgets");
    
    var task_div = document.createElement("div");
    task_div.className = "task_line";
    task_div.id = task_id;
    

    widgets_div.appendChild(task_div);

    // Create a form for the content 

    var form_id = "form_" +task_id;
    var form_div = _create_task_form(form_id);
    task_div.appendChild(form_div);

    var dlg = document.querySelector( "#" + form_id);
    var inputs = dlg.querySelectorAll("input");
    var title_input = inputs[0];


    var dlg_buttons = {
            "Update": function() {
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
    			console.log("Update " + constellation_name + "/" + task_id);
                update_task(constellation_name, task_id,
                       title, ros_package,launch, timeout, args, latency, 
                       uplink_data_cap, downlink_data_cap,
                       local_start,
                       local_stop,
                       vrc_id,
                       vrc_num); 
                
                $( this ).dialog( "close" );
                 },
            "Duplicate": function() {
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
                console.log("Create duplicate task " + constellation_name + "/" + task_id);
                create_task(constellation_name, 
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
      height: 550,
      width: 500,
      modal: true,
      buttons: dlg_buttons,

      open: function() { 
                    console.log("open!!");
                    $("#tabs_" + form_id).tabs();
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

        var readOnly = false;
        // Disable editing for users
        if(get_user_info().role == "user")
        {
            readOnly = true;
        }

        if(task.task_state != "ready")
        {
            readOnly = true;
        }

        for (var i=0; i< 12; i++)
        {
            inputs[i].readOnly = readOnly;
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
            page_refresh();
        }
    };
    
    x_button.onclick =  function()
    {
        var r=confirm('Delete task?'  );
        if (r==false)
        {
            return;
        }
        delete_task(constellation_name, task_id);
        
    };


	var title_text_span = document.createElement("span"); // document.createTextNode(task_title);
	title_text_span.innerHTML = task_title;
    var task_table = document.createElement("table");

    task_table.style.width="100%";
	
    var tbl_body = document.createElement("tbody");
	var row = document.createElement("tr");
	var cell_left = document.createElement("td");
	cell_left.align="left;"
	var cell_right = document.createElement("td");
	cell_right.align = "right";
	//cell_right.style.width ="20%";

	task_table.appendChild(tbl_body);
	tbl_body.appendChild(row);
	row.appendChild(cell_left);
	
	row.appendChild(cell_right);
	
	cell_left.appendChild(state_widget);
	cell_left.appendChild(title_text_span);
	
	cell_right.appendChild(action_button);
	cell_right.appendChild(edit_button);
	cell_right.appendChild(x_button);

	task_div.appendChild(task_table);

    var count = 0;
    var cb = function(event, data)
    {
    	
        if(data.constellation_name != constellation_name)
            return;

        var tasks = data.tasks;
        var task = _find_task_data(task_id, tasks);
        if(task)
        {
        	// Create a string with the task title and score message
        	var task_display_msg = "<b>" + task.task_title + "</b>";
        	task_display_msg += " " + task.task_message;
        	
            if(task_display_msg != title_text_span.innerHTML )
            {
            	title_text_span.innerHTML = task_display_msg;
            }

            //  console.log('TASK _set_state_widget: ' + constellation_name + ': '+ task.task_state)
            state_widget.src = "/js/images/gray_status.png";
            if (task.task_state == "running" || task.task_state == "starting")
            {
            	// colors =  ["/js/images/gray_status.png", "/js/images/blue_status.png"];
            	colors =  ["/js/images/blue_status.png", "/js/images/blue_status.png"];

            	// Starting up color
            	if(data.gazebo == "not running")
            	{
            		// colors[1] =  "/js/images/yellow_status.png";
            		colors[1] =  "/js/images/gray_status.png";
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
                
                // Constellation is ready
                if(data.constellation_state == "running")
                {
                	// No other task running
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
            
            // The count is used to blink the status
            if (count == 100) 
                 count =0;
             else 
                 count ++;
        }
        else
        {
            // Task does not exist anymore
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
