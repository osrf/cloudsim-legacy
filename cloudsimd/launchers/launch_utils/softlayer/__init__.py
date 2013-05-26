import os
import time
import SoftLayer.API
import unittest
import json
import subprocess
import shutil
import datetime
import commands
import redis
import logging
from pprint import pprint
from SoftLayer.exceptions import SoftLayerAPIError


def log(msg, channel="softlayer"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
        print("softlayer>",msg)
    except:
        print("Warning: redis not installed.")
    #print("cloudsim log> %s" % msg)


class SoftLayerException(Exception):
    pass


def get_softlayer_path():
    d = os.path.dirname(__file__)
    r = os.path.abspath(d +'../../../../../../softlayer.json')
    return r


def _get_hardware(api_username, api_key, server_name = None):
    domain_id = None   
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

    count = 0
    done = False
    hardware = None
    while not done:
        try:
            client = SoftLayer.API.Client('SoftLayer_Account', domain_id, api_username, api_key)
            client.set_object_mask(object_mask)
            hardware = client.getHardware()
            done = True
        except:
            time.sleep(10)
            count += 1
            if count > 20:
                raise SoftLayerException("Can't enumerate SoftLayer hardware after %s retries" % (count+1) )
    return hardware


def _send_reload_server_cmd(api_username, api_key, server_name, server_id):
    for i in range(100):
        try:
            client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id,
                                      api_username,
                                      api_key)
            try:
                result = client.reloadCurrentOperatingSystemConfiguration('FORCE')
                log("Reload of %s returned %s" % (server_name, result))
                return result
            except SoftLayerAPIError, e:
                if str(e).find("outstanding transaction") > 0:
                    log("Reload of %s skipped due to outstanding transaction" % server_name)
                    return True
                else:
                    raise

        except Exception, e:
            log("%s" % e)
            time.sleep(10)
    raise SoftLayerException("Can't enable public ip on server %s", server_name)


def _send_shutdown_public_port(api_username, api_key, server_name, server_id):
    for i in range(100):
        client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id,
                                      api_username, api_key)
        result = False
        try:
            result = client.setPublicNetworkInterfaceSpeed(0)
            print (result)
            return result
        except Exception, e:
            log("%s" % e)
            time.sleep(10)
    raise SoftLayerException("Can't enable public ip on server %s", server_name)


def _send_enable_public_port(api_username, api_key, server_name, server_id):
    for i in range(100):
        client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id,
                                      api_username, api_key)
        result = False
        try:
            result = client.setPublicNetworkInterfaceSpeed(10000)
            log("_send_enable_public_port %s = %s" % (server_name, result))
            return result
        except Exception, e:
            if str(e).find("outstanding transaction") > 0:
                log("_send_enable_public_port of %s skipped due to outstanding transaction" % server_name)
                return True
            else:
                raise
            log("%s" % e)
            time.sleep(10)
    raise SoftLayerException("Can't enable public ip on server %s", server_name)


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
    print('cwd: %s'%(os.getcwd()))
    if st != 0:
        print(cmd)
        raise SoftLayerException(cmd)
    print("RETURN %s" % st)
    print ("%s" % output)
    print("copying keys")


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


class aTestSofty(unittest.TestCase):
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


    def stest_softlayer(self):
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

        count = 1
        for i in range(count):
            print ("\n\n%s" % i)
            client = SoftLayer.API.Client('SoftLayer_Account', None, "hugo", '')
            client.set_object_mask(object_mask)
            hardware = client.getHardware()

            print('ACCOUNT 1')
            print([x['hostname'] for x in hardware] )
            print("")

            client = SoftLayer.API.Client('SoftLayer_Account', None, 'osrf', '')
            client.set_object_mask(object_mask)
            hardware = client.getHardware()

            print('ACCOUNT 2')
            print([x['hostname'] for x in hardware] )


    def atest_single(self):
        #client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, api_username, api_key)
        # server_id = client.findByIpAddress(server_ip)['id']
        #result = client.reloadCurrentOperatingSystemConfiguration('FORCE')
        #print (result)
        server_ip = "75.126.125.26"
        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)

        client = SoftLayer.API.Client('SoftLayer_Hardware_Server', None, osrf_creds['user'], osrf_creds['api_key'])

        x = client.findByIpAddress(server_ip)
        print(x['hostname'])
        print(x['primaryIpAddress'])
        print(x['id'])
        for i in x.iteritems():
            print(i)

    def stest_phil(self):
        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)
        server_name = "cs-01"

        client = SoftLayer.Client(username=osrf_creds['user'], api_key=osrf_creds['api_key'],)
        hardware = client['Account'].getHardware( filter={'hardware': {'hostname': {'operation': server_name}}})
        pprint(hardware)

        server = client['Hardware'].getObject(id=hardware[0]['id'],
                                               mask="operatingSystem.passwords.password, primaryIpAddress")

        print("\n\nDETAILS")
        pprint(server)
        id = server['id']
        public_ip = server['primaryIpAddress']
        password = None
        try:
            password = server['operatingSystem']['passwords'][0]['password']
        except:
            pass

        print ("")
        print(id)
        print(public_ip)
        print(password)

    def atest_list(self):
        object_mask = {}
        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)

        count = 1
        for i in range(count):
            client = SoftLayer.API.Client('SoftLayer_Account', None, osrf_creds['user'], osrf_creds['api_key'])
            client.set_object_mask(object_mask)
            hardware = client.getHardware()
            #print(client.findByHostname("cs-01"))
            for server in hardware:
                print("")
                #print(server['hostname'])
                #print(server['id'])
                #privateIpAddress
                for k,v in server.iteritems():
                    print(k,":",v )
            print("done\n\n")

    def atest_ubuntu_upload_and_execute(self):
        pass

def softlayer_dash_board(osrf_creds, show_transactions = True):

    def pr(server):
        print ("  %10s %s ssh root@%s" % (server[1], server[3], server[5] ))
        if show_transactions:
            server_id = server[0]
            server_name = server[1]
            client = SoftLayer.API.Client('SoftLayer_Hardware_Server', server_id, osrf_creds['user'], osrf_creds['api_key'])
            t = client.getActiveTransaction()
            if t:
                for k, v in t.iteritems():
                    print("              * %s: %s" % (k,v))


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


def reload_servers(osrf_creds, server_names):

    client = SoftLayer.Client(username=osrf_creds['user'],
                              api_key=osrf_creds['api_key'],)
    
    
    for server_name in server_names:
        hardware = client['Account'].getHardware(filter={'hardware':
                                    {'hostname': {'operation': server_name}}})
        server_id = hardware[0]['id']
        print("reloading server %s id %s" % (server_name, server_id))
        _send_reload_server_cmd(osrf_creds['user'], osrf_creds['api_key'],
                                    server_name, server_id)




def get_constellation_prefixes(osrf_creds):
    """
    SoftLayer credentials give access to a set of machines (constellation).
    This functions returns the list of constellation (by counting the routers)
    """
    for i in range(100):
        object_mask = {}
        client = SoftLayer.API.Client('SoftLayer_Account', 
                        None, osrf_creds['user'], osrf_creds['api_key'])
        client.set_object_mask(object_mask)
        servers = client.getHardware()
        routers = [s['hostname'] for s in servers if s['hostname'].startswith('router-') ]
        cloudsims = [s['hostname'] for s in servers if s['hostname'].startswith('cs-') ]

        cs_prefixes = [x.split('-')[1] for x in cloudsims]
        prefixes = [x.split('-')[1] for x in routers]
        return cs_prefixes, prefixes
        time.sleep(5)
    raise SoftLayerException("Can't enumerate servers (100 retries)")


def shutdown_public_ips(osrf_creds, server_names):

    for server_name in server_names:
        hardware = _get_server_hardware(osrf_creds, server_name)
        server_id = hardware[0]['id']
        _send_shutdown_public_port(osrf_creds['user'],
                                   osrf_creds['api_key'],
                                   server_name,
                                   server_id)


def enable_public_ips(osrf_creds, server_names):

    for server_name in server_names:
        hardware = _get_server_hardware(osrf_creds, server_name)
        server_id = hardware[0]['id']
        _send_enable_public_port(osrf_creds['user'],
                                   osrf_creds['api_key'],
                                   server_name,
                                   server_id)


def wait_for_server_reloads(osrf_creds, server_names, callback=print_cb):
    api_username = osrf_creds['user'] 
    api_key = osrf_creds['api_key']

    server_ids_to_hostname = {} 

    for server_name in server_names:
        hardware = _get_server_hardware(osrf_creds, server_name)
        pprint(hardware)
        server_id = hardware[0]['id']
        hostname = hardware[0]['hostname']
        server_ids_to_hostname[server_id] = hostname

    _wait_for_multiple_server_reloads(api_username, api_key,
                                      server_ids_to_hostname,
                                      callback)


def _get_server_hardware(osrf_creds, server_name):
    for i in range(100):
        try:
            client = SoftLayer.Client(username=osrf_creds['user'],
                                      api_key=osrf_creds['api_key'],)
            hardware = client['Account'].getHardware(filter={
                    'hardware': {'hostname': {'operation': server_name}}})
            return hardware
        except Exception, e:
            time.sleep(10)
            log("Retry %s/100 %s" % (i, e))
    raise SoftLayerException("Can't get server info for %s" % server_name)


def _get_server_user_object(osrf_creds,  server_name, sid):
    for i in range(100):
        try:
            client = SoftLayer.Client(username=osrf_creds['user'], 
                            api_key=osrf_creds['api_key'],)
            server = client['Hardware'].getObject(id=sid, 
                mask="operatingSystem.passwords.password, primaryIpAddress")
            return server
        except Exception, e:
            time.sleep(10)
            log("Retry %s/100 %s" % (i, e))
    raise SoftLayerException(
                         "Can't get server object for %s" % server_name)


def get_machine_login_info(osrf_creds, server_name):

    hardware = _get_server_hardware(osrf_creds, server_name)
    sid = hardware[0]['id']
    server = _get_server_user_object(osrf_creds, server_name, sid)

    public_ip = server['primaryIpAddress']

    priv_ip = server['privateIpAddress']
    password = None
    try:
        password = server['operatingSystem']['passwords'][0]['password']
    except:
        pass

    print(public_ip)
    print(password)

    return public_ip, priv_ip, password


class sTestSoftLayer(unittest.TestCase):

    def atest_list_loop(self):

        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)
        prefixes = get_constellation_prefixes(osrf_creds)
        print("prefixes")
        pprint(prefixes)
        self.assertTrue(len(prefixes) > 0, "no constellations")

    def atest_get_machine_login_info(self):
        server = "fc1-14"
        osrf_creds = load_osrf_creds(get_softlayer_path())
        x = get_machine_login_info(osrf_creds, server)

        self.assertTrue(len(x) == 3, 'did not get creds')

    def atest_wait_for_server_reloads(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        servers = ['cs-14', 'sim-14', 'fc1-14', 'fc2-14']
        wait_for_server_reloads(osrf_creds, servers)

    def etest_reload_Server(self):
        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)
        servers = ['cs-43', 'sim-43', 'router-43', 'fc1-43', 'fc2-43']
        try:
            reload_servers(osrf_creds, servers)
        except Exception, e:
            print e

    def stest_shutdown_public_ip(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        servers = ['cs-44', 'sim-44', 'fc1-44', 'fc2-44']
        shutdown_public_ips(osrf_creds, servers)

    def test_enable_public_ip(self):
        osrf_creds = load_osrf_creds(get_softlayer_path())
        servers = ['sim-44', 'fc1-44', 'fc2-39']
        enable_public_ips(osrf_creds, servers)

    def atest_get_constellation_prefixes(self):
        p = get_softlayer_path()
        osrf_creds = load_osrf_creds(p)
        prefixes = get_constellation_prefixes(osrf_creds)

        self.assertTrue(len(prefixes) > 0, "no constellations")

if __name__ == "__main__":

    p = get_softlayer_path()
    osrf_creds = load_osrf_creds(p)
#   softlayer_dash_board(osrf_creds)
    unittest.main()


