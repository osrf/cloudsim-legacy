
var machine_configurations = null;

function add_cloud_credentials_widget(place_holder_div_name)
{

    var launch_div = document.getElementById(place_holder_div_name);
    var str  = '<h2>Amazon Web Services credentials</h2>'; 
    str += '';
    
    str += 'Account name <input type="text" name="account_name"/>';
    str += 'Access key <input type="text" name="access_key"/>';
    str += 'Secret access key <input type="text" name="secret_access_key"/>';
    // str += 'Availability zone <input type="text" name="availability_zone"/>';
    str += '<br>default availability zones: N. Virginia: ';
    str += '<select name="us_east_1_az">';
    str += '<option value="us-east-1a">us-east-1a</option>';
    str += '<option value="us-east-1b">us-east-1b</option>';
    str += '<option value="us-east-1c">us-east-1c</option>';
    str += '<option value="us-east-1d">us-east-1d</option>';
    str += '</select>';

    str += ' Ireland:';
    str += '<select name="eu_west_1_az">';    
    str += '<option value="eu-west-1a">eu-west-1a</option>';
    str += '<option value="eu-west-1b">eu-west-1b</option>';
    str += '<option value="eu-west-1c">eu-west-1c</option>';
    str += '</select>';
    
//    str += '<h3>Oregon default availability zones</h3>';
//    str += '<select name="us_west_2_az">';
//    str += '<option value="us-west-2a">us-west-2a</option>';
//    str += '<option value="us-west-2b">us-west-2b</option>';
//    str += '<option value="us-west-2c">us-west-2c</option>';
//    str += '</select>';
//    str += '<option value="nova">nova</option>';
    
    str += '<br><button type="button" onclick="_cred_click(\'';
    str += place_holder_div_name;
    str += '\');">Add account</button><br><br>Set new AWS credentials and availability zone. Those changes will be applied on the new constellations';

    launch_div.innerHTML = str;
    console.log('cloud_credentials_on_load_page:' +  place_holder_div_name);
}

function _cred_click(div_name)
{
    console.log('_cred_click')
    var div = document.getElementById(div_name);
    var inputs = div.querySelectorAll("input");
    var account_name = inputs[0].value;
    var access = inputs[1].value;
    var secret_access = inputs[2].value;
    
    var selects = div.querySelectorAll("select");
    var us_east_az = selects[0].value;
    var eu_west_az = selects[1].value;
    var r = add_aws_credentials(account_name, access, secret_access, us_east_az, eu_west_az);
    
    alert(r['msg']);
}

