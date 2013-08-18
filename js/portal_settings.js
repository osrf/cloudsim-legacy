
var machine_configurations = null;

function add_portal_settings_widget(place_holder_div_name)
{

    var the_div = document.getElementById(place_holder_div_name);
    
    var portal = get_portal_info();
    var hostname = portal['hostname']
    var team = portal['team']
    var str  = '<h2>OSRF Portal</h2>'; 
    str += '';
    str += 'Hostname <input type="text" name="hostname" ';
    str += 'value= "' + hostname  +'"/>';
    str += 'team <input type="text" name="team" ';
    str += ' value="' + team + '"'
    str +=  '/>';


    str += '<button type="button" onclick="_portal_click(\'';
    str += place_holder_div_name;

    str += '\');">Override</button><br><br>Set portal information.';
    // str += 'Leave blank to skip the log generation process';

    the_div.innerHTML = str;
    console.log('add_portal_settings_widget:' +  place_holder_div_name);
    
    
}

function _portal_click(div_name)
{
    console.log('_portal_click')
    var div = document.getElementById(div_name);
    
    var hostname = div.querySelectorAll("input")[0].value;
    var team = div.querySelectorAll("input")[1].value;
    var r = set_portal_info(hostname, team);
    
    alert(r['msg']);
}

