
var machine_configurations = null;

function add_cloud_credentials_widget(place_holder_div_name)
{
    var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs.py");
    machine_configurations = eval( '(' + x + ')' );
        
    var launch_div = document.getElementById(place_holder_div_name);
    var str  = '<h2>Amazon EC2 credentials</h2>'; 
    str += '';
    str += 'Access key <input type="text" name="access_key"/>';
    str += 'Secret access key <input type="text" name="secret_access_key"/>';
    
    str += '<button type="button" onclick="_cred_click(\'';
    str += place_holder_div_name;
    str += '\');">Override</button>';
    
    launch_div.innerHTML = str;
    console.log('cloud_credentials_on_load_page:' +  place_holder_div_name);
}


function change_credentials(access_key, secret_access_key)
{
    var key = encodeURIComponent(access_key);
    var secret = encodeURIComponent(secret_access_key);
    var url = '/cloudsim/inside/cgi-bin/cloud_credentials?access_key=';
    url += key+'&secret_access_key=' + secret;
    console.log(url);
    var msg = httpPut(url);
    
    var jmsg = eval('(' + msg + ')');
    console.log("change_credentials: " + msg);
    alert(jmsg['msg']);
}

function _cred_click(div_name)
{
     
    var div = document.getElementById(div_name);
    
    var access = div.querySelectorAll("input")[0].value;
    var secret_access = div.querySelectorAll("input")[1].value;
    change_credentials(access, secret_access);
}

