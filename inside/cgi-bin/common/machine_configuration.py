import unittest
import json
import os
#import common    

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
    def __init__(self, email, configs_dir = MACHINE_CONFIG_DIR):
        self.user = email
        self.domain = email.split('@')[1]
        self.configs_dir = configs_dir
        
    def get_configs(self):
        configs = {}
        config_files = os.listdir(self.configs_dir)
        for short_name in config_files:
            fname = os.path.join(self.configs_dir, short_name)
            config = Machine_configuration.from_file(fname)
            configs[short_name] = config
        return configs
            
    def get_configs_as_json(self):
        configs = self.get_configs()
        str = "{"
        for name, cfg in configs.items():
            str += name
            str += ":" 
            str += cfg.as_json()
            str += ","
        str += "}"    
        return str
                       
class ConfigsCase(unittest.TestCase):
        
    def test_config(self):
        
        config = Machine_configuration()
        config.initialize(root_directory = 'test_pems', 
                                         credentials_ec2 = '../../../../boto.ini', 
                                         image_id ="ami-137bcf7a", 
                                         instance_type = 't1.micro' , 
                                         security_groups = ['ping_ssh'], 
                                         username = 'ubuntu', 
                                         distro = 'precise')
        fname = "test_machine.config"
        config.save_json(fname)
        
        config2 = Machine_configuration.from_file(fname)
        print("\nfrom file:")
        config2.print_cfg()
        self.assertEqual(config.image_id, config2.image_id, "json fail")

    def get_config_dir(self):
        config_dir = os.path.join(os.path.split(__file__)[0], '../../../distfiles/configs')
        self.assert_(os.path.exists(config_dir), '%s does not exist' % config_dir)
        return config_dir
            
    
    def test_make_configs(self):
        
        startup_script = ""
        
        config = Machine_configuration()
        config.initialize(  root_directory = common.MACHINES_DIR, 
                     credentials_ec2 = common.BOTO_CONFIG_FILE_USEAST, 
                     image_id ="ami-98fa58f1", 
                     instance_type = 'cg1.4xlarge' , 
                     security_groups = ['openvpn'], 
                     username = 'ubuntu', 
                     distro = 'precise')
        
        config_dir = self.get_config_dir()
        fname = os.path.join(config_dir, 'simulation_gpu')
        print("Saving to '%s'" % fname)
        config.save_json(fname)
        
        
        
        config_test = Machine_configuration()
        config_test.initialize(   root_directory = common.MACHINES_DIR, 
                     credentials_ec2 = common.BOTO_CONFIG_FILE_USEAST, 
                     image_id ="ami-98fa58f1", 
                     instance_type = 't1.micro' , 
                     security_groups = ['openvpn'], 
                     username = 'ubuntu', 
                     distro = 'precise',
                     startup_script = "#!/bin/bash\necho hello > test.txt\n\n")
        
        config_dir = self.get_config_dir()
        fname = os.path.join(config_dir, 'empty_micro_vpn')
        print("Saving to '%s'" % fname)
        config_test.save_json(fname)
        
    def test_configsdb(self):
        
        configs_dir = self.get_config_dir()
        cdb = ConfigsDb('toto@cloud.com',configs_dir)
        
        cfgs = cdb.get_configs()
        self.assert_(len(cfgs)>0, "empty configs db")
        
        json_str = cdb.get_configs_as_json()
        print json_str
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()  