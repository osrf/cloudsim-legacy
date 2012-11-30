
function users_admin_on_load_page(users_div_name)
{

	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    
	var users_div = document.getElementById(users_div_name);
	var str  = '<h2>Users</h2>'; 
    
	str += "<ul>";
	for(var user in users)
    {
		var role = users[user];
		str += '<li>';
        str += user;
        str += " <b>" + role + "</b>"; 
        str += '<button type="button" onclick="_remove_user(\'' + user + '\');">X</button>';
        str += '</li>';
    }
	str +="</ul>";
	


    str += '<input type="text" name="new_user"/>';
    str += '<select id="role_"' + user + ' />';
    str += '   <option value="user" selected="selected">user</option>';
    str += '   <option value="admin">admin</option>';
    str += '</select>';
    
    str += '<button type="button" onclick="_add_click(';
    str += "'" +  users_div_name + "'";
    str +=');">Add user</button>';
    
    users_div.innerHTML = str;

    $.subscribe("/cloudsim", function(event, data){
    	if(data.type == 'admin')
    	{
    		console.log("Admin action: " + data.action);
    		users_admin_on_load_page(users_div_name);
    	}
        
    });
    
}


function _add_click(users_div_name)
{
    var users_div = document.getElementById(users_div_name);
    var input = users_div.querySelector("input");
    var user = input.value;
    var select = users_div.querySelector("select");
    var role = select.value;
    _add_user(user, role);
}


function _add_user(user_name, role)
{
	var req = "/cloudsim/inside/cgi-bin/user?user=" + user_name;
	req +="&role=" + role;
	var x = httpPost(req);
	console.log(x);
	
}

function _remove_user(user_name)
{
	var x = httpDelete("/cloudsim/inside/cgi-bin/user?user=" + user_name);
	console.log(x);
	
	
}

