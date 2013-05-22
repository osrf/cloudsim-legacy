import os
import time
import SoftLayer.API
import unittest
import json
import subprocess
import shutil
import datetime
import commands


class SoftLayerException(Exception):
    pass


def get_softlayer_path():
    d = os.path.dirname(__file__)
    r = os.path.abspath(d +'../../../../../../softlayer.json' )
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
            #'processorCount' : {},
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


def _send_shutdown_public_port(api_username, api_key, server_id):
    client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, api_username, api_key)
    # server_id = client.findByIpAddress(server_ip)['id']
    #result = client.shutdownPublicPort()
    result = client.setPublicNetworkInterfaceSpeed(0)
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
    stat = t['transactionStatus']
    name = stat['name']
    if stat.has_key('friendlyName'):
        name = stat['friendlyName']
    return name


def _get_pub_ip(server):
    for nic in server['frontendNetworkComponents']:
        if nic.has_key('primaryIpAddress'):
            ip = nic['primaryIpAddress']
            return ip
    return None

def _get_priv_ip(server):
    for nic in server['backendNetworkComponents']:
        if nic.has_key('primaryIpAddress'):
            ip = nic['primaryIpAddress']
            return ip
    return None

def get_servers_info(osrf_creds):
    servers = []
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)  
    for server in hardware:
        host = server['hostname']
        username = None
        password = None
        user = None
        if 'operatingSystem' in server:
            o_s = server['operatingSystem']
            if o_s['passwords']:
                user = o_s['passwords'][0]
                username = user['username']
                password = user['password']

        priv_ip = _get_priv_ip(server)
        pub_ip = _get_pub_ip(server)
        server_id = server['id']
        servers.append((server_id, host, username, password, priv_ip, pub_ip)  )
        #print "[%7s] %10s [%s, %10s] [%s / %s]" % (server_id, host, username, password, priv_ip, pub_ip)
    return servers


def hardware_info(osrf_creds):
    servers = get_servers_info(osrf_creds)
    
    for server in servers:
        server_id, host, username, password, priv_ip, pub_ip = server
        print ("[%7s] %10s [%s, %10s] [%s / %s]" % (server_id, host, username, password, priv_ip, pub_ip))


def _extract_prefixes(servers):
    routers = [s[1] for s in servers if s[1].startswith('router-') ]
    prefixes = [x.split('-')[1] for x in routers]
    return prefixes


def get_constellation_prefixes(osrf_creds):
    """
    SoftLayer credentials give access to a set of machines (constellation).
    This functions returns the list of constellation (by counting the routers)
    """
    servers = get_servers_info(osrf_creds)
    prefixes = _extract_prefixes(servers)
    return prefixes
    
        
def hardware_helpers(osrf_creds):
    servers = get_servers_info(osrf_creds)
    for server in servers:
        server_id, host, username, password, priv_ip, pub_ip = server
        print("")
        print("# %s [%s /%s] %s" % (host,pub_ip, priv_ip, password))
        print("# id: %s user: %s" %(server_id, username))
        prefix = host.split("-")[0]
        print("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=2 -i key-%s.pem ubuntu@%s" % (prefix, pub_ip ) )
        print("ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -o ConnectTimeout=2 -i key-%s.pem ubuntu@%s" % (prefix, priv_ip ) )


def softlayer_server_scan(osrf_creds):
    servers = get_servers_info(osrf_creds)
    for server  in servers:
        server_id = server[0]
        server_name = server[1]
        client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, osrf_creds['user'], osrf_creds['api_key'])
        print(server_name, server_id, client.getActiveTransaction())

    
def print_cb(server_name, status):
    print("PCB %s  [%s] = %s" % (datetime.datetime.now(),server_name, status))


def _wait_for_multiple_server_reloads(api_username, api_key, server_ids_to_hostname, callback):

    status = ""
    booting_servers = {server_id:status for server_id in server_ids_to_hostname.keys()}

    while booting_servers:
        try:
            ready_servers = []
            for server_id, status in booting_servers.iteritems():
                
                current_status = _get_boot_status(api_username, api_key, server_id)
                # check for status change
                hostname = server_ids_to_hostname[server_id]
                if status != current_status:
                    booting_servers[server_id]=current_status
                    callback(hostname, current_status)
                if current_status == "ready":
                    print("%s reloaded" % hostname)
                    ready_servers.append(server_id)
            
            for server_id in ready_servers:
                booting_servers.pop(server_id)
            time.sleep(10)
        except:
            pass
        
def reload_servers(osrf_creds, machine_names):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)
    server_ids_to_hostname = {server['id']:server['hostname'] for server in hardware if server['hostname'] in machine_names}
    for server_id in server_ids_to_hostname.keys():
        _send_reload_server_cmd(api_username, api_key, server_id)
    

def shutdown_public_ips(osrf_creds, machine_names):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)
    server_ids_to_hostname = {server['id']:server['hostname'] for server in hardware if server['hostname'] in machine_names}
    for server_id in server_ids_to_hostname.keys():
        _send_shutdown_public_port(api_username, api_key, server_id)
        
def get_machine_login_info(osrf_creds, machine):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
   
    hardware = _get_hardware(api_username, api_key)
    server = [server for server in hardware if server['hostname']==machine][0]
    os = server['operatingSystem']
    user = None
    if len(os['passwords']):
        user = os['passwords'][0]
    pub_ip = _get_pub_ip(server) 
    priv_ip = _get_priv_ip(server)
    psswd = None
    if user:
        psswd = user['password']
    return pub_ip, priv_ip, psswd
    
def get_cloudsin_ip(osrf_creds, constellation_id):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    machine = "cs_%s" % constellation_id      
    hardware = _get_hardware(api_username, api_key)
    ip = [server['frontendNetworkComponents'][-1]['primaryIpAddress'] for server in hardware if server['hostname']==machine][0]  
    return ip

def create_openvpn_key(key_fname):
    cmd = 'openvpn --genkey --secret %s' % key_fname
    print(cmd)
    st,output = commands.getstatusoutput(cmd)
    if st != 0:
        raise SoftLayerException(cmd)

def create_ssh_key(key_prefix, target_directory ):
    path = os.path.join(target_directory, key_prefix)
    cmd = 'ssh-keygen -q -t rsa -f %s.pem -N ""' % path
    print(cmd)
    st,output = commands.getstatusoutput(cmd)
    if st != 0:
        raise SoftLayerException(cmd)


def setup_ssh_key_access(ip, root_password, key_path):
    """
    Generates a key, logs in the machine at ip as root,
    creates a ubuntu user (sudoer) and adds the key  
    """
    l = [os.path.dirname( __file__),'bash', 'auto_ubuntu.bash']
    fname = os.path.join(*l)
    
    
    cmd = "%s %s %s %s" % (fname, ip, root_password, key_path)
    print("calling: %s\nip: %s\npsswd: %s\nkey: %s" % (fname, ip, root_password, key_path))
    
    
    st,output = commands.getstatusoutput(cmd)
    if st != 0:
        print(cmd)
        raise SoftLayerException(cmd)
    print("RETURN %s" % st)
    print ("%s" % output)
    print("copying keys")
        
#    l = [os.path.dirname( __file__),'bash', '%s.pem' % key_prefix]
#    src = os.path.join(*l)
#    shutil.move(src, target_directory)
#    
#    l = [os.path.dirname( __file__),'bash', '%s.pem.pub' % key_prefix]
#    src = os.path.join(*l)
#    shutil.move(src, target_directory)
    


class SoftLayerCredentials(object):
    """
    Class that manages the SoftLayer credentials.
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


def wait_for_server_reloads(osrf_creds, machine_names, callback = print_cb):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']
    hardware = _get_hardware(api_username, api_key)
    server_ids_to_hostname = {server['id']:server['hostname'] for server in hardware if server['hostname'] in machine_names}
    _wait_for_multiple_server_reloads(api_username, api_key, server_ids_to_hostname, callback)



class TestSofty(unittest.TestCase):
    
    def atest_get_constellation_prefixes(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        prefixes = get_constellation_prefixes(osrf_creds)
        print prefixes
    
    def atest_shutdown_public_ip(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        machine_names = ["sim-02", "fc1-02", "fc2-02"]
        shutdown_public_ips(osrf_creds, machine_names)

    def atest_ssh_setup(self):
        
        ip = '50.97.149.39'
        d = os.path.abspath('.')
        create_ssh_key('test-key', d)
        key_path = os.path.join(d,'test-key.pem.pub')
        setup_ssh_key_access(ip, 'SapRekx3', key_path )
        router_priv_key_path = os.path.join(d,'test-key.pem')
        print ("ssh -i %s ubuntu@%s" % (router_priv_key_path, ip))


    def atest_a_write_cred(self):
        fname = get_softlayer_path()
        c = SoftLayerCredentials('hugo','xxx', fname)
        c.save()

        creds = load_osrf_creds(fname)
        print(creds)


    def stest_reload_xx(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        machine_names = ['router-17', 'fc1-17', 'fc2-17', 'sim-17']
        reload_servers(osrf_creds, machine_names)
        wait_for_server_reloads(osrf_creds, machine_names, print_cb)

    def stest_reload_bxx(self):

        osrf_creds = load_osrf_creds(get_softlayer_path())
        machine_names = ['router-01', 'fc1-01', 'fc2-01', 'sim-01']
        wait_for_server_reloads(osrf_creds, machine_names, print_cb)

    def atest_user_setup(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        print("ubuntu user setup")
        machine = "router-01"
        dst_dir = os.path.abspath('.')
        key_prefix = 'key_%s' %  machine
        ip, priv_ip, password = get_machine_login_info(osrf_creds, machine)

        #
        # must create key first now :-)

        print("%s %s : %s" % (machine, ip, password))
        setup_ssh_key_access(ip, password, key_prefix)
        print ("ssh -i %s/%s.pem ubuntu@%s" % (dst_dir, key_prefix, ip))

    def atest_validate(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        api_username = osrf_creds['user'] 
        api_key = osrf_creds['api_key']
        domain_id = None
        client = SoftLayer.API.Client('SoftLayer_Account', domain_id, api_username, api_key)
        valid = True 
        try:
            x = client['Account'].getObject()
            print(x)
        except Exception, e:
            valid = False
            print("not valid: %s" % e)

        print(valid)

    def test_softlayer(self):

        
        object_mask = {
            'hardware' : {
                'operatingSystem' : {
                    'passwords' : {},
                },
                
                'frontendNetworkComponents' :{},
                'backendNetworkComponents' :{},
                'datacenter' : {},
                # 'processorCount' : {},
            }
        }


        client = SoftLayer.API.Client('SoftLayer_Account', None, "hugo", 'b990c28ad6b37fc5d142ddabe44790b62aed80e84d9dc5df6d1d81e1083c991e')
        client.set_object_mask(object_mask)
        hardware = client.getHardware()
        
        print('ACCOUNT 1')
        print([x['hostname'] for x in hardware] )
        print()

        client = SoftLayer.API.Client('SoftLayer_Account', None, 'osrf', 'a3d642ae81e46b8bb1ef9fbcef6804660ab6e5fd5d5b21a27973ba299973ba4f')
        client.set_object_mask(object_mask)
        hardware = client.getHardware()
        
        print('ACCOUNT 2')
        print([x['hostname'] for x in hardware] )

        

    def atest_ubuntu_upload_and_execute(self):
        pass
#        print("ubuntu user setup")
#        ip, password = get_machine_login_info(osrf_creds, "fc1-01")
#        setup_ssh_key_access(ip, password, 'fc1_key')
#
#        print("ubuntu user setup")
#        ip, password = get_machine_login_info(osrf_creds, "fc2-01")
#        setup_ssh_key_access(ip, password, 'fc2_key')
#
#        print("ubuntu user setup")
#        ip, password = get_machine_login_info(osrf_creds, "sim-01")
#        setup_ssh_key_access(ip, password, 'sim_key')


def softlayer_dash_board(osrf_creds):

    def pr(server):
        print ("   %10s %s ssh root@%s" % (server[1], server[3], server[5] ))

    def get_server(name):
        server = [s for s in servers if s[1] == name][0]
        return server

    # osrf_creds = load_osrf_creds(soft_layer_creds_fname)
    servers = get_servers_info(osrf_creds)
    prefixes = _extract_prefixes(servers)

    for i in range(5):
        print('')

    for prefix in prefixes:
        try:
            print('')
            print("constellation %s" % prefix)
            fc1 = get_server('fc1-%s' % prefix)
            fc2 = get_server('fc2-%s' % prefix)
            sim = get_server('sim-%s' % prefix)
            router = get_server('router-%s' % prefix)
            cs = get_server('cs-%s' % prefix)

            pr(cs)
            pr(router)
            pr(sim)
            pr(fc1)
            pr(fc2)
        except:
            print(" ERROR ")

if __name__ == "__main__":

    p = get_softlayer_path()
    osrf_creds = load_osrf_creds(p)
    softlayer_dash_board(osrf_creds)
    softlayer_server_scan(osrf_creds)

    unittest.main()

    #hardware_helpers(osrf_creds)
    #hardware_info(osrf_creds)


