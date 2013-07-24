
var machine_configurations = null;

function add_osrf_cloud_credentials_widget(place_holder_div_name)
{

    //var x = httpGet("/cloudsim/inside/cgi-bin/machine_configs");
    //machine_configurations = eval( '(' + x + ')' );
    var the_div = document.getElementById(place_holder_div_name);
    var str  = '<h2>SoftLayer credentials</h2>'; 
    str += '';
    str += 'Name <input type="text" name="user"/>';
    str += 'API key <input type="text" name="api_key"/>';
    str += '<button type="button">Override</button><br><br>Set new credentials. Those changes will be used for each new constellations';
    the_div.innerHTML = str;
    
    var button = the_div.querySelector("button");
    button.onclick = function ()
    {
        console.log('_osrf_cred_click')
        
        var user = the_div.querySelectorAll("input")[0].value;
        var api_key = the_div.querySelectorAll("input")[1].value;
        var r = change_osrf_credentials(user, api_key);
        alert(r['msg']);
    }

    console.log('osrf_cloud_credentials_on_load_page:' +  place_holder_div_name);
}

