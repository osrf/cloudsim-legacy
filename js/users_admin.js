
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
    str += "<table class='tablesorter' cellspacing='0'>";
    str += "<thead><tr><th>User Email</th><th>Role</th><th>Actions</th></tr></thead>";
    str += "<tbody>";
    
    for(var user in users)
    {
    	var role = users[user];
	str += "<tr>";
    	str += '<td>';
        str += user;
        str += "</td><td> <b>" + role + "</b></td><td>"; 
        str += '<button type="button" style="background: url(/cloudsim/js/images/icn_trash.png) no-repeat; border:none;cursor:pointer;" onclick="remove_user(\'' + user + '\');">&nbsp;</button>';
        str += '</td>';
	str +="</tr>";
    }
    
    str += "</tbody></table>";
    
    return str;
}

function _get_user_div_str(users_div_name, users)
{

    var str = "<div id='user_list'>";
    
    str += _get_user_list_str(users);
    
    str +="</div>";
    str += "<div class='module_content'>";
    str += "<fieldset style='padding-right:5%;'>";
    str += "<label>New User\'s Gmail Address</label>";
    str += '<input type="text" name="new_user"/>';
    str += "</fieldset>";
    str += "<fieldset style='width:48%; float:left; margin-right: 3%; margin-top: 0;'>";
    str += "<label>User's Role</label>";
    str += '<select id="role" style="width:92%;"/>';
    str += '   <option value="user" selected="selected">User</option>';
    str += '   <option value="officer">Officer</option>';
    str += '   <option value="admin">Administrator</option>';
    str += '</select>';
    str += "</fieldset>";
    str += '<button type="button" style="background: #3573c0; color: white; font: bold 14px; padding: 4px; cursor: pointer; -moz-border-radius: 4px; -webkit-border-radius: 4px;" onclick="_add_click(';
    str += "'" +  users_div_name + "'";
    str +=');">Add user</button><br><br>Do not remove the last remaining administrative user!';
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
    add_user(user, role);
    
    // perform an update 
	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    var str = _get_user_list_str(users)
	user_list_div.innerHTML = str;
 }