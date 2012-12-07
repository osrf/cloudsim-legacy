from __future__ import with_statement
from __future__ import print_function

import unittest
import json
import os
from constants import MACHINES_DIR, BOTO_CONFIG_FILE_USEAST
from constants import CONFIGS_DIR
#import common    
from  testing import get_test_runner

MACHINE_CONFIG_DIR = '/var/www-cloudsim-auth/configs'
       
class Machine_configuration(object):

    @classmethod
    def from_file(cls, fname):
        with open(fname,'r') as fp:
            dict = json.load(fp)
            #x = Machine_configuration(**dict)
            x = Machine_configuration()
            x.__dict__.update(dict)
            return x
    
    def __init__(self):
        pass
        
    def initialize(self, 
                 image_id,
                 instance_type,
                 security_groups,
                 username,
                 distro,
                 startup_script,
                 ip_retries,
                 ssh_retries):

        # launching parameters
        #self.credentials_ec2 = credentials_ec2 # boto file
        #self.root_directory = root_directory
        self.image_id = image_id
        self.instance_type = instance_type
        self.security_groups = security_groups
        self.username = username
        self.distro = distro
        self.startup_script = startup_script
        self.ip_retries = ip_retries
        self.ssh_retries = ssh_retries
        
    
    def as_json(self):
        str = json.dumps(self.__dict__)
        return str
        
    def save_json(self, fname):
        
        with open(fname,'w') as fp:
            #json.dump(self.__dict__, fp) #, skipkeys, ensure_ascii, check_circular, allow_nan, cls, indent, separators, encoding, default)
            fp.write(self.as_json())
            fp.close()

    def print_cfg(self):
        print("Machine configuration")
        for item in self.__dict__:
            print ("%s: %s" % (item, self.__dict__[item]) )
    

 
class ConfigsDb(object):
    def __init__(self, email, configs_dir=CONFIGS_DIR):
        self.user = email
        self.domain = email.split('@')[1]
        self.configs_dir = configs_dir
        
    def get_config_dir(self):
        return self.configs_dir
    
    def get_configs(self):
        configs = {}

        launcher_modules = list(set([x.split(".py")[0] for x in os.listdir(self.configs_dir)]))
        launcher_modules.remove("__init__")
        
        for module in launcher_modules:
            configs[module] = {'description': 'n/a'}
        
        configs['gazebo'] = {'description': "A GPU instance with ROS installed (and the ROS version of Gazebo, 1.0)"} 
        configs['micro_vpn'] = {'description': "A non gpu machine with VPN but no simulator"}
        configs['drc_sim_latest'] = {'description': "A GPU machine with the latest ROS-fuerte, Gazebo and DRC simulation packages installed"}
        configs['cloudsim'] = {'description': "A micro instance that runs the Cloudsim web app"}
        return configs

    def get_configs_as_json(self):
        configs = self.get_configs()
        str = json.dumps(configs)
        return str
                       
class ConfigsCase(unittest.TestCase):

        
    def test_configsdb(self):
        
        # configs_dir = self.get_config_dir()
        cdb = ConfigsDb('toto@cloud.com')
        
        cfgs = cdb.get_configs()
        self.assert_(len(cfgs)>0, "empty configs db")
        
        json_str = cdb.get_configs_as_json()
        print (json_str)
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main(testRunner = get_runner())   