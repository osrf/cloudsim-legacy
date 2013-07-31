
var machine_configurations = null;

function add_cloud_credentials_widget(place_holder_div_name)
{

    var launch_div = document.getElementById(place_holder_div_name);
    var str  = '<h2>Amazon Web Services credentials</h2>'; 
    str += '';
    str += 'Access key <input type="text" name="access_key"/>';
    str += 'Secret access key <input type="text" name="secret_access_key"/>';
    // str += 'Availability zone <input type="text" name="availability_zone"/>';
    str += 'Availability zone <select name="availability_zone">';
    str += '<option value="us-east-1a">us-east-1a</option>';
    str += '<option value="us-east-1b">us-east-1b</option>';
    str += '<option value="us-east-1c">us-east-1c</option>';
    str += '<option value="us-east-1d">us-east-1d</option>';
    str += '<option value="eu-west-1a">eu-west-1a</option>';
    str += '<option value="eu-west-1b">eu-west-1b</option>';
    str += '<option value="eu-west-1c">eu-west-1c</option>';
    str += '<option value="nova">nova</option>';
    str += '</select>';
    str += '<button type="button" onclick="_cred_click(\'';
    str += place_holder_div_name;

    str += '\');">Override</button><br><br>Set new AWS credentials and availability zone. Those changes will be applied on the new constellations';
    

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
    var r = change_aws_credentials(access, secret_access, availability_zone);
    
    alert(r['msg']);
}

