


function create_constellations_widget(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    var div = document.getElementById(div_name);
    
    
    var str = "<h2>Constellations</h2>";
    str += '<div id="task-view-form" title="Task properties">';
    //str += '<p>Hola</p>';
    str += '<b>Simulation properties</b><br>';
    str += 'ROS Package<br><input type="text" name="package"></input><br>';
    str += 'Launch file<br><input type="text" name="launch"></input><br>';
    str += 'Arguments<br><input type="text" name="args"></input><br>';
    str += '<b>Network properties</b><br>';
    str += 'Target latency (ms)<br><input type="text" name="latency"></input><br>';
    str += '</div>';

//    str += '<div id="task-add-form" title="Add task">';
//    str += '<input type="text"></input>'
//    str += '</div>';

    div.innerHTML = str;

//    var task_form_div = document.createElement("div");
//    task_form_div.id = "task-add-form";
//    task_form_div.title = "Add task";
//
//    var ipack = document.createElement("input"); //input element, text
//
//    var txtNode = document.createTextNode("Hello");
//    ipack.setAttribute('type',"text");
//    ipack.setAttribute('name',"package");
//    
//    task_form_div.appendChild(txtNode);
//    task_form_div.appendChild(ipack);
//    
//    div.appendChild(task_form_div);
    


    $.subscribe("/constellation", function(event, data){
        if(data.constellation_name)
        {
            var constellation = data.constellation_name;
            var configuration = data.configuration; 
            //data.constellation_config;
            var constellation_div =  div.querySelector("#"+constellation);
            if( constellation_div == null)
            {
                create_constellation(div_name, configuration, constellation);
            }
        }
    });

    // initialise the form that shows the tasks properties
    $( "#task-view-form" ).dialog({
      autoOpen: false,
      height: 400,
      width: 350,
      modal: true,
      buttons: {
         "Save": function() {
         var dlg = document.querySelector("#task-view-form");
         var inputs = dlg.querySelectorAll("input");
         var task_data = {
            'ros_package' : inputs[0].value,
            'launch' : inputs[1].value,
            'args' : inputs[2].value,
            'latency' : inputs[3].value
         }
//         var ros_package = inputs[0].value;
//         var launch = inputs[1].value;
//         var args = inputs[2].value;
//         var latency = inputs[3].value;
         
         alert(task_data.ros_package + ", " + task_data.launch + ", " + task_data.args  + ", " + task_data.latency);
         
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
}



//function get_constellation_names(div_name)
//{
//    var constellations = [];
//    // look at the children 'div' they are named after the
//    // constellation
//    var div = document.getElementById(div_name);
//    var nodes = div.childNodes; // getElementsByTagName('div');
//    for(var i=0; i<nodes.length; i++) {
//        var node = nodes[i];
//        var title = node.id;
//        if(title != undefined)
//        {
//            constellations.push(title);
//        }
//    }
//    return constellations;
//}

function insert_constellation_div(div_name, configuration_name, constellation_name)
{
    var div = document.getElementById(div_name);
    var nodes = div.childNodes;
    var node = null;
    for(var i=0; i<nodes.length; i++) 
    {
        node = nodes[i];
        var constellation_iter = node.id;
        if(constellation_iter == undefined)
            continue;
        var cmp = constellation_iter.localeCompare(constellation_name);
        // console.log(constellation_iter+ " comp " + constellation + " = " + cmp);

        // Found it :-) 
        if(cmp == 0)
            return node;

        // found where to create it :-)
        if(cmp > 0)
            break;

        // makes insertBefore at the end
        node = null;
    }
    
    var const_div = document.createElement("div");
    const_div.id = constellation_name;
    _set_const_style(const_div.style);
    
    var top_div = document.createElement("div");
    top_div.id = "top";
    
    var title_str = " <h3 style=' margin-top:0; margin-bottom:0;'><center>";
    title_str    +=   constellation_name + " [" + configuration_name + "]</center></h3>";
    
    top_div.style.backgroundColor ="#44497a";
    top_div.style.borderTopLeftRadius = "15px";
    top_div.style.borderTopRightRadius = "15px";
    top_div.style.color = "white";
    top_div.style.marginTop = "0";
    top_div.style.color = "0";
    
    top_div.innerHTML = title_str;
    const_div.appendChild(top_div);
    
    // div.insertBefore(top_div, node);
    var msg_div = document.createElement("div");
    msg_div.id = "error";
    msg_div.style.color = "red";
    const_div.appendChild(msg_div);

    var terminate_button= document.createElement('input');
    terminate_button.setAttribute('type','button');
    terminate_button.setAttribute('value','Terminate');

    terminate_button.onclick =  function()
    {   
        var r = confirm("terminate " + constellation_name + "?");
        if (r==false)
        {
            return;
        }
        terminate_constellation(constellation_name);
    };
    
    const_div.appendChild(terminate_button);

    var add_task_button =document.createElement('input');
    add_task_button.setAttribute('type','button');
    add_task_button.setAttribute('value','Add task...');
    add_task_button.onclick =  function()
    {
         $( "#task-view-form" ).dialog( "open" );
    }
    
    const_div.appendChild(add_task_button);
    

    var tasks_div = document.createElement("div");
    tasks_div.id = "tasks";
    const_div.appendChild(tasks_div);

    var machines_div = document.createElement("div");
    machines_div.id = "machines";
    const_div.appendChild(machines_div);
     

    // const_div.innerHTML = _get_constellation_div_str(div_name, configuration, constellation);
    div.insertBefore(const_div, node);
    
    return const_div;
}



function _constellation_terminate(div_name, constellation_name)
{
    var r = confirm("terminate " + constellation_name + "?");
    if (r==false)
    {
        return;
    }
    terminate_constellation(constellation_name);
}


function constellation_remove(div_name, constellation_name)
{
    var div = document.getElementById(div_name);
    var constellation = div.querySelector("#"+constellation_name);
    div.removeChild(constellation);   
}


function _set_const_style(style)
{
    style.width = "98%";
    style.float = "left";
    style.border="1px solid #535453";
    style.borderRadius = "15px";
    style.margin = "1%";
    style.backgroundColor = "#a8a7a7"; // f1f1f2
}


