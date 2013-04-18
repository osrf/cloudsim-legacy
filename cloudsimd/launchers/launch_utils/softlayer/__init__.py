import os
import time
import SoftLayer.API
import unittest
import json


def get_softlayer_path():
    d = os.path.dirname(__file__)
    r = os.path.abspath(d +'../../../../../../softlayer.ini' )
    return r
    

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

def _wait_for_server_reload(api_username, api_key, server_id, callback):
    
    status = None
    while True:
        time.sleep(10)
        new_status = _get_boot_status(api_username, api_key, server_id)
        if new_status != status:
            status = new_status
            callback(server_id, status)
            if status == "ready":
                return 


def _get_boot_status(api_username, api_key, server_id):
    client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, api_username, api_key)
    t = client.getActiveTransaction()
    if t == '':
        return "ready"
    name = t['transactionStatus']['friendlyName']
    return name

def hardware_info(osrf_creds):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)  
    for server in hardware:
        host = server['hostname']
        user = server['operatingSystem']['passwords'][0]
        priv_ip = None
        pub_ip = None
        for nic in server['backendNetworkComponents']:
            if nic.has_key('primaryIpAddress'):
                priv_ip = nic['primaryIpAddress']
        for nic in server['frontendNetworkComponents']:
            if nic.has_key('primaryIpAddress'):
                pub_ip = nic['primaryIpAddress']
        server_id = server['id']
        print "[%7s] %10s [%s, %10s] [%s / %s]" % (server_id, host, user['username'], user['password'], priv_ip, pub_ip)

def _wait_for_multiple_server_reloads(api_username, api_key, server_list):
    
    time.sleep(5)
    booting_servers = server_list[:]
    while booting_servers:
        time.sleep(30)
        for server_id in booting_servers:
            if not  _is_booting(api_username, api_key, server_id):
                print("%s reloaded" % server_id)
                booting_servers.remove(server_id)
        
    
     
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


class SoftLayerCredentials(object):
    """
    Class that manages all the AWS credentials.
    """

    def __init__(self,
                 name,
                 api_key,
                 fname):
        self.fname = fname
        self.osrf_creds = {'user':name, 'api_key': api_key}
 
        
    def save(self):
        with open(self.fname, 'w') as f:
            s = json.dumps(self.osrf_creds)
            f.write(s)
    
    
def load_osrf_creds(fname):
    path = fname
    with open(path,'r') as f:
        s = f.read()
        j = json.loads(s)
        return j


    
class TestSofty(unittest.TestCase):
    
    def atest_write_cred(self):
        fname = get_softlayer_path()
        c = SoftLayerCredentials('hugo','xxx', fname)
        c.save()
        
        creds = load_osrf_creds(fname)
    
    def test_reload_fc2_xx(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        machine_names = ['fc2-xx']
        reload_servers(osrf_creds, machine_names)
        
    
    def test_o(self):
        print("%s" % os.path.dirname( __file__))
        _setup_ssh_key_access('33.33', 'pass', 'key.key')

if __name__ == "__main__": 
    p = get_softlayer_path()
    osrf_creds = load_osrf_creds(p)
    hardware_info(osrf_creds)
    unittest.main()
