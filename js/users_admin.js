
function add_users_admin_widget(users_div_name)
{

	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    
	var users_div = document.getElementById(users_div_name);
	var str = _get_user_div_str(users_div_name, users);
    users_div.innerHTML = str;
	
	var user_list_div = users_div.querySelector("#user_list");
	
    $.subscribe("/users", function(event, data)
    {
    	var str = _get_user_list_str(data)
    	user_list_div.innerHTML = str;
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
        str += '<button type="button" onclick="remove_user(\'' + user + '\');">X</button>';
        str += '</li>';
    }
    str +="</ul>";
    return str;
}

function _get_user_div_str(users_div_name, users)
{
	var str  = '<h2>Users</h2>';
    str += "<div id='user_list'>";
    
    str += _get_user_list_str(users);
    
    str +="</div>";
    
    str += 'New User\'s Gmail Address: <input type="text" name="new_user"/>';
    str += '<select id="role" />';
    str += '   <option value="user" selected="selected">simulation user</option>';
    str += '   <option value="admin">administrator</option>';
    str += '   <option value="officer">simulations officer</option>';
    str += '</select>';
    
    str += '<button type="button" onclick="_add_click(';
    str += "'" +  users_div_name + "'";
    str +=');">Add user</button><br><br>Add or remove users. Do not remove the last remaining administrative user!';
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
    add_user(user, role);
    
    // perform an update 
	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    var str = _get_user_list_str(users)
	user_list_div.innerHTML = str;
 }



