
var machine_configurations = null;

function add_osrf_cloud_credentials_widget(place_holder_div_name)
{

    var the_div = document.getElementById(place_holder_div_name);
    var str = '<fieldset style="padding-right:5%;">';
    str += '<label>Name</label>';
    str += '<input type="text" name="user"/>';
    str += '</fieldset>';
    str += '<fieldset style="padding-right:5%;">';
    str += '<label>API Key</label>';
    str += '<input type="text" name="api_key"/>';
    str += '</fieldset>';
    str += '<button type="button" style="background: #3573c0; color: white; font: bold 14px; padding: 4px; cursor: pointer; -moz-border-radius: 4px; -webkit-border-radius: 4px;">Override</button>';
    str += '<p>Set new credentials. Those changes will be used for each new constellations</p>';
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

