
var machine_configurations = null;

function add_portal_settings_widget(place_holder_div_name)
{

    //var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs");
    //machine_configurations = eval( '(' + x + ')' );
    var the_div = document.getElementById(place_holder_div_name);
    var str  = '<h2>OSRF cloud robotics credentials</h2>'; 
    str += '';
    str += 'Username <input type="text" name="user"/>';
    str += 'API key <input type="text" name="api_key"/>';
    // str += 'Availability zone <input type="text" name="availability_zone"/>';
    str += 'Location <select name="location">';
    str += '<option value="us-east-1a">Dallas</option>';
    str += '</select>';
    str += '<button type="button" onclick="_portal_click(\'';
    str += place_holder_div_name;

    str += '\');">Override</button><br><br>Set new credentials. Those changes will be used for each new constellations';
    the_div.innerHTML = str;
    console.log('osrf_cloud_credentials_on_load_page:' +  place_holder_div_name);
    
    
}

function _portal_click(div_name)
{
    console.log('_portal_click')
    var div = document.getElementById(div_name);
    
    var user = div.querySelectorAll("input")[0].value;
    var api_key = div.querySelectorAll("input")[1].value;
    var location = div.querySelectorAll("select")[0].value;
    var r = change_osrf_credentials(user, api_key, location);
    
    alert(r['msg']);
}

