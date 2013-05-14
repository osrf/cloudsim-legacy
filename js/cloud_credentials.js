
var machine_configurations = null;

function add_cloud_credentials_widget(place_holder_div_name)
{

    var launch_div = document.getElementById(place_holder_div_name);
    var str = '<fieldset style="padding-right:5%;">';
    str += '<label>Access Key</label>';
    str += '<input type="text" name="access_key"/>';
    str += '</fieldset>';
    
    str += '<fieldset style="padding-right:5%;">';
    str += '<label>Secret Access Key</label>';
    str += '<input type="text" name="secret_access_key"/>';
    str += '</fieldset>';
    str += '<fieldset style="width:48%; float:left; margin-right: 3%; margin-top: 0;">';
    str += '<label>Availability Zone</label>';
    str += '<select style="width:92%;" name="availability_zone">';
    str += '<option value="us-east-1a">us-east-1a</option>';
    str += '<option value="us-east-1b">us-east-1b</option>';
    str += '<option value="us-east-1c">us-east-1c</option>';
    str += '<option value="us-east-1d">us-east-1d</option>';
    str += '<option value="eu-west-1a">eu-west-1a</option>';
    str += '<option value="eu-west-1b">eu-west-1b</option>';
    str += '<option value="eu-west-1c">eu-west-1c</option>';
    str += '</select>';
    str += '</fieldset>';
    str += '<button type="button" style="background: #3573c0; color: white; font: bold 14px; padding: 4px; cursor: pointer; -moz-border-radius: 4px; -webkit-border-radius: 4px;" onclick="_cred_click(\'';
    str += place_holder_div_name;
    str += '\');">Override</button><p style="float:left;">Set new AWS credentials and availability zone. Those changes will be applied on the new constellations</p>';
    
    

    launch_div.innerHTML = str;
    console.log('cloud_credentials_on_load_page:' +  place_holder_div_name);
}

function _cred_click(div_name)
{
    console.log('_cred_click')
    var div = document.getElementById(div_name);
    
    var access = div.querySelectorAll("input")[0].value;
    var secret_access = div.querySelectorAll("input")[1].value;
    var availability_zone = div.querySelectorAll("select")[0].value;
    var r = change_credentials(access, secret_access, availability_zone);
    
    alert(r['msg']);
}

