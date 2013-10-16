
// 
// the auth_type is either OpenID or Basic
function add_users_admin_widget(users_div_name, auth_type)
{

	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    
	var users_div = document.getElementById(users_div_name);
	
	var str = _get_user_div_str(users_div_name, users, auth_type);
		
	users_div.innerHTML = str;
	
	var user_list_div = users_div.querySelector("#user_list");
	
	var old_str = "";
    $.subscribe("/users", function(event, data)
    {
    	var str = _get_user_list_str(data)
    	if (str != old_str)
    	{
    		old_str = 
    		user_list_div.innerHTML = str;
    	}
    });
}


function _get_user_list_str(users)
{
	
	var str  = '';
    str += "<ul>";
    for(var user in users)
    {
    	var role = users[user];
    	str += '<li>';
        str += user;
        str += " <b>" + role + "</b>"; 
        
        var button_state = "";
        if (role == "admin")
    	if (get_user_info()['role'] == 'officer')
    	{
    		button_state = "disabled";
    	}
    	str += '<button type="button" onclick="remove_user_click(\'' + user + '\');" ' + button_state + '>X</button>';
    	str += '</li>';
    }
    str +="</ul>";
    return str;
}

function remove_user_click(user)
{
	var users = get_users();
	var admin_count = 0;
	for(var u in users)
	{
		if(user != u)
		{
			if(users[u] == "admin")
			{
				admin_count += 1;
			}
		}
	}
	if (admin_count == 0)
	{
		alert("It is not possible to delete the last user!");
		return;
	}
	remove_user(user);
}

function _get_user_div_str(users_div_name, users, auth_type)
{
	var str  = '<h2>Users</h2>';
    str += "<div id='user_list'>";
    str += _get_user_list_str(users);
    str +="</div>";
    
    str += '<div>' ; //  class= "second_level_container">';
    
//    str += '<h3>Add new user</h3>';
    if(auth_type == "OpenID")
    {
    	str += "New User's Gmail Address:";
    }	
    else
    {
    	str += 'Add user:';
    }
    str += ' <input type="text" name="new_user"/>';

    if(auth_type != "OpenID")
    {
//    	str += "<br>";
    	str += 'Password: <input type="password" name="passwd1"/>'
//    	str += "<br>";
    	str += 'Retype Password: <input type="password" name="passwd2"/>'
//    	str += "<br>";
    }
    
//    str += "<br>";
    str += "Role: ";
    str += '<select id="role" />';
    str += '   <option value="user" selected="selected">simulation user</option>';
    str += '   <option value="admin">administrator</option>';
    str += '   <option value="officer">simulations officer</option>';
    str += '</select>';
    
//    str += "<br>"
    str += '<button type="button" onclick="_add_click(';
    str += "'" +  users_div_name + "'";
    str +=');">Add user</button>';
    
    // str +='<br><br>Add or remove users. Do not remove the last remaining administrative user!';
    
    str +="</div>";
    
    return str;
}


function _add_click(users_div_name)
{
    var users_div = document.getElementById(users_div_name);
    var user_list_div = users_div.querySelector("#user_list");
    var input = users_div.querySelector("input");
    var user = input.value;
    var select = users_div.querySelector("select");
    var role = select.value;

    var pass1 = users_div.querySelector('input[name="passwd1"]')
    var pass2 = users_div.querySelector('input[name="passwd2"]')

    var password;
    if (pass1 && pass2)
    {
    	var p1 = pass1.value;
    	var p2 = pass2.value;
    	if (p1 == p2)
    	{
    		password = p1;
    	}
    	else
    	{
    		alert("passwords don't match!");
    	}
    }
    add_user(user, role, password);

    // perform an update 
	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    var str = _get_user_list_str(users)
	user_list_div.innerHTML = str;
}




