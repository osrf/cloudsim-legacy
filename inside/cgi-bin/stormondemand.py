from __future__ import print_function
import urllib2
import json
import subprocess
import tempfile
import os

SOD_API_BASEURL = 'https://api.stormondemand.com'
SOD_API_VERSION = '1.0/'
SOD_API_URL = '%s/%s'%(SOD_API_BASEURL, SOD_API_VERSION)

DEFAULT_TEMPLATE = 'UBUNTU_1204_UNMANAGED'
DEFAULT_ZONE = 15 # Zone A, US West
DEFAULT_CONFIG_ID = 5 # 8GB 4-core VM
DEFAULT_DOMAINNAME = 'osrfoundation.org'
DEFAULT_SUBACCNT_TYPE = 'test'

# Map generic machine types to Storm's IDs
MACHINE_TYPES = {
    'vm-small' : None,
    'vm-medium' : 5, # 8GB 4-core VM
    'vm-large' : None,
    'vm-xlarge' : None,
    'gpu' : None
}
# Map generic distro types to Storm's names
DISTROS = {
    'ubuntu-natty' : None,
    'ubuntu-precise' : 'UBUNTU_1204_UNMANAGED'
}

class StormOnDemand:
    def __init__(self, username, password):
        self.username = username

        # Auth code cribbed from http://docs.python.org/howto/urllib2.html#id6
        pw_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        pw_mgr.add_password(None, SOD_API_URL, username, password)
        handler = urllib2.HTTPBasicAuthHandler(pw_mgr)
        # Use this opener for all API calls
        self.urlopener = urllib2.build_opener(handler)

    def _generate_password(self):
        # Cribbed from http://www.frihost.com/forums/vt-132022.html
        import random, string
        f = lambda x, y: ''.join([x[random.randint(0,len(x)-1)] for i in xrange(y)])
        pw = f(list(string.ascii_letters+string.digits), 12)

        # Make sure that we meet Storm's password requirements:
        # "A password of at least 7 characters and up to 30 characters in length, containing no spaces. Must contain 3 of the 4 following classes: lowercase, uppercase, numbers and punctuation."
        if not(set(pw) & set(string.digits)):
            pw += '0'
        if not(set(pw) & set(string.ascii_uppercase)):
            pw += 'A'
        if not(set(pw) & set(string.ascii_lowercase)):
            pw += 'a'
        return pw

    def _make_url(self, suffix):
        url = '%s%s'%(SOD_API_URL, suffix)
        return url

    def _call(self, api_url, params=None):
        url = self._make_url(api_url)
        if params:
            params_dict = {}
            params_dict['params'] = params
            enc_data = json.dumps(params_dict)
        else:
            enc_data = None
        if enc_data:
            request = urllib2.Request(url, enc_data)
            r = self.urlopener.open(request)
        else:
            r = self.urlopener.open(url)
        return json.loads(r.read())

    def ping(self):
        return self._call('utilities/info/ping')

    def version(self):
        return self._call('utilities/info/version')

    def server_list(self):
        return self._call('server/list')

    def server_available(self, domain):
        return self._call('server/available', {'domain': domain})

    def storm_server_create(self, 
                            backup_enabled=0,
                            bandwidth_quota=0, 
                            config_id=DEFAULT_CONFIG_ID, 
                            domain=DEFAULT_DOMAINNAME,
                            image_id=None, 
                            ip_count=1,
                            template=DEFAULT_TEMPLATE, 
                            zone=DEFAULT_ZONE):
        params = {}
        params['backup_enabled'] = backup_enabled
        params['bandwidth_quota'] = bandwidth_quota
        params['config_id'] = config_id
        params['domain'] = domain
        if image_id:
            params['image_id'] = image_id
        params['ip_count'] = ip_count
        params['template'] = template
        params['zone'] = zone

        # Root password, which we won't use
        password = self._generate_password()
        params['password'] = password
        # ssh key
        keyfile = tempfile.NamedTemporaryFile(delete=False)
        keyfile.close()
        # Not strictly a safe thing to do...
        os.unlink(keyfile.name)
        cmd = ['ssh-keygen', '-P', '', '-f', keyfile.name]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = po.communicate()
        if po.returncode != 0:
            raise Exception(err)
        privkey = open(keyfile.name).read()
        pubkey = open('%s.pub'%(keyfile.name)).read()
        params['public_ssh_key'] = pubkey
        ret = self._call('storm/server/create', params)
        print(ret)
        return (privkey, ret)

    def storm_config_list(self, baremetal=False):
        if baremetal:
            return self._call('storm/config/baremetal/list')
        else:
            return self._call('storm/config/list')

    # Provider-independent API below
    def create_server(self, machine_type, distro):
        config_id = MACHINE_TYPES[machine_type]
        template = DISTROS[distro]
        privkey, ret = self.storm_server_create(config_id=config_id, template=template)
        machine_id = ret['uniq_id']
        # TODO: loop on Storm/server/details(machine_id) until we get good data, then
        # extract ipaddress
        ipaddress = None
        return (privkey, ipaddress, machine_id)

    def stop_server(self, machine_id):
        return self._call('storm/server/shutdown', {'uniq_id': machine_id})

    def start_server(self, machine_id):
        return self._call('storm/server/start', {'uniq_id': machine_id})

    def destroy_server(self, machine_id):
        return self._call('storm/server/destroy', {'uniq_id': machine_id})

