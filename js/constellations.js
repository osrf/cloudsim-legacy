

function create_constellations_widget(div_name)
{
    console.log("constellations_on_load_page " + div_name);
    
    var div = document.getElementById(div_name);
    
    var str = "<h2>Constellations</h2>";
    str += '<div id="task-view-form" title="Task properties"></div>';
    
    div.innerHTML = str;
    
    //var dialog_div = document.createElement("div");
    //dialog_div.id = "task-view-form";

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
      height: 300,
      width: 350,
      modal: true,
      buttons: {
        "Update": function() {
          var bValid = true;
          
          // allFields.removeClass( "ui-state-error" );
          bValid = true;
          
          /*
          bValid = bValid && checkLength( name, "username", 3, 16 );
          bValid = bValid && checkLength( email, "email", 6, 80 );
          bValid = bValid && checkLength( password, "password", 5, 16 );
 
          bValid = bValid && checkRegexp( name, /^[a-z]([0-9a-z_])+$/i, "Username may consist of a-z, 0-9, underscores, begin with a letter." );
          // From jquery.validate.js (by joern), contributed by Scott Gonzalez: http://projects.scottsplayground.com/email_address_validation/
          bValid = bValid && checkRegexp( email, /^((([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+(\.([a-z]|\d|[!#\$%&'\*\+\-\/=\?\^_`{\|}~]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])+)*)|((\x22)((((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(([\x01-\x08\x0b\x0c\x0e-\x1f\x7f]|\x21|[\x23-\x5b]|[\x5d-\x7e]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(\\([\x01-\x09\x0b\x0c\x0d-\x7f]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF]))))*(((\x20|\x09)*(\x0d\x0a))?(\x20|\x09)+)?(\x22)))@((([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|\d|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.)+(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])|(([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])([a-z]|\d|-|\.|_|~|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])*([a-z]|[\u00A0-\uD7FF\uF900-\uFDCF\uFDF0-\uFFEF])))\.?$/i, "eg. ui@jquery.com" );
          bValid = bValid && checkRegexp( password, /^([0-9a-zA-Z])+$/, "Password field only allow : a-z 0-9" );
          */
        	  
          if ( bValid ) 
          {
            $( "#users tbody" ).append( "<tr>" +
              "<td>" + name.val() + "</td>" +
              "<td>" + email.val() + "</td>" +
              "<td>" + password.val() + "</td>" +
            "</tr>" );
            $( this ).dialog( "close" );
          }
        },
        
        "Delete" : function() {
            alert("What the hell are you trying to do?");
        }
        
      //  Cancel: function() {
      //    $( this ).dialog( "close" );
      //  }
      },
      close: function() {
       //    allFields.val( "" ).removeClass( "ui-state-error" );
    	  console.log("gone");
      }
    });
}



function get_constellation_names(div_name)
{
    var constellations = [];
    // look at the children 'div' they are named after the
    // constellation
    var div = document.getElementById(div_name);
    var nodes = div.childNodes; // getElementsByTagName('div');
    for(var i=0; i<nodes.length; i++) {
        var node = nodes[i];
        var title = node.id;
        if(title != undefined)
        {
            constellations.push(title);
        }
    }
    return constellations;
}

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


