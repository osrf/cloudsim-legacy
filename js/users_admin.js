
function users_admin_on_load_page(users_div_name)
{

	var x = httpGet("/cloudsim/inside/cgi-bin/users.py");
    users = eval( '(' + x + ')' );
    
	var users_div = document.getElementById(users_div_name);
	var str  = '<h2>Users</h2>'; 
    
	str += "<ul>";
	for(var i=0;  i < users.length; i++)
    {
		var user = users[i];
        str += '<li>' + user;
        str += '<button type="button" onclick="_remove_user(\'' + user + '\');">X</button>'
        str += '</li>';
    }
	str +="</ul>";

    str += '<input type="text" name="new_user"/><button type="button" onclick="_add_click(';
    str += "'" +  users_div_name + "'";
    str +=')">Add user</button>';
    
    users_div.innerHTML = str;

    $.subscribe("/users/modify", function(event){
    	console.log("users/modify");
    	users_admin_on_load_page(users_div_name);
    });
   
}

function users_admin_event(str_data)
{

	var data = eval( '(' + str_data + ')' );
	if(data.type == 'admin')
	{
		console.log(str_data);
		$.publish("/users/modify");
	}
}

function _add_click(users_div_name)
{
    var users_div = document.getElementById(users_div_name);
    var input = users_div.querySelector("input");
    var user = input.value;
    _add_user(user);
}


function _add_user(user_name)
{
	var x = httpPost("/cloudsim/inside/cgi-bin/user?user=" + user_name);
	console.log(x);
	
}

function _remove_user(user_name)
{
	var x = httpDelete("/cloudsim/inside/cgi-bin/user?user=" + user_name);
	console.log(x);
	
	
}

