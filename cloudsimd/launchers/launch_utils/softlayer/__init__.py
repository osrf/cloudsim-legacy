import os
import time
import SoftLayer.API
import unittest


def _get_hardware(api_username, api_key, server_name = None):
    domain_id = None   
    client = SoftLayer.API.Client('SoftLayer_Account', domain_id, api_username, api_key)
    object_mask = {                                                
        'hardware' : {
            'operatingSystem' : {
                'passwords' : {},
            },
            #'networkComponents' : {},
            'frontendNetworkComponents' :{},
            'backendNetworkComponents' :{},
            'datacenter' : {},
            'processorCount' : {},
        }
    }
    client.set_object_mask(object_mask)
    hardware = client.getHardware()
    return hardware

def _send_reload_server_cmd(api_username, api_key, server_id):
    client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, api_username, api_key)
    # server_id = client.findByIpAddress(server_ip)['id']
    result = client.reloadCurrentOperatingSystemConfiguration('FORCE')
    print (result)

def _wair_for_server_reload(api_username, api_key, server_id):
    time.sleep(3600)


def hardware_info(osrf_creds):
    hardware = _get_hardware(osrf_creds)  
    for server in hardware:
        host = server['hostname']
        user = server['operatingSystem']['passwords'][0]
        priv_ip = server['backendNetworkComponents'][-1]['primaryIpAddress']
        pub_ip = server['frontendNetworkComponents'][-1]['primaryIpAddress']
        server_id = server['id']
        print "[%7s] %10s [%s, %10s] [%s / %s]" % (server_id, host, user['username'], user['password'], priv_ip, pub_ip)

def _wait_for_multiple_server_reloads(api_username, api_key, server_list):
    time.sleep(3600)  
    
     
def reload_servers(osrf_creds, machine_names):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)
    servers = [server['id'] for server in hardware if server['hostname'] in machine_names]
    for server in servers:
        _send_reload_server_cmd(api_username, api_key, server)
    _wait_for_multiple_server_reloads(api_username, api_key, servers)
  

def reload_constellation(osrf_creds, constellation_id):
    router = "router_%s" % constellation_id
    sim = "sim_%s" % constellation_id
    fc1 = "fc1_%s" % constellation_id
    fc2 = "fc2_%s" % constellation_id
    machine_names = [router, sim, fc1, fc2]
    reload_servers(osrf_creds, machine_names)


def get_machine_login_info(osrf_creds, machine):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
   
    hardware = _get_hardware(api_username, api_key)
    sever = [server for server in hardware if server['hostname']==machine][0]
    user = server['operatingSystem']['passwords'][0]
    ip = server['frontendNetworkComponents'][-1]['primaryIpAddress']
    psswd = user['password']
    return ip,psswd
    
def get_cloudsin_ip(osrf_creds, constellation_id):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    machine = "cs_%s" % constellation_id      
    hardware = _get_hardware(api_username, api_key)
    ip = [server['frontendNetworkComponents'][-1]['primaryIpAddress'] for server in hardware if server['hostname']==machine][0]  
    return ip

def _setup_ssh_key_access(ip, root_password, key_fname, ):
    """
    Generates a key, logs in the machine at ip as root,
    creates a ubuntu user (sudoer) and adds the key  
    """
    l = [os.path.dirname( __file__),'bash', 'auto_ubuntu.bash']
    fname = os.path.join(*l)
    print("oula: %s" % fname)
    #subprocess.check_call(cmd.split())

class TestSofty(unittest.TestCase):
    
    def test_o(self):
        print("%s" % os.path.dirname( __file__))
        _setup_ssh_key_access('33.33', 'pass', 'key.key')

if __name__ == "__main__": 
    osrf_creds = {'user':'hugo', 'api_key': 'ef658539df1e05a72ff3a717d98cce8faf1b47bfa27adb2ef8619ad56e1998aa'}
    # hardware_info(osrf_creds)
    unittest.main()
