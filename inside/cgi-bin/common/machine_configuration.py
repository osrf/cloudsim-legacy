import json
import redis

class ConfigsDb(object):
    def __init__(self, email):
        self.user = email
        self.domain = email.split('@')[1]
         
        
    def get_config_dir(self):
        return self.configs_dir
    
    def get_configs(self):
        configs = {}
        configs['vpc_micro_trio'] = {'description': "test constellation with 3 micro machines"} 
        configs['vpc_trio_prerelease'] = {'description': "test constellation with 3 micro machines"} 
        configs['vpc_trio'] = {'description': "3 machines: a gpu field computer, a router and a gpu simulator"}
        configs['simulator'] = {'description': "1 machine: gpu computer with the latest ROS-fuerte, Gazebo and DRC simulation packages installed"}
        configs['simulator_prerelease'] = {'description': "1 machine: gpu computer with the latest ROS-fuerte, Gazebo and DRC pre-release simulation packages installed"}
        configs['cloudsim'] = {'description': "A CloudSim web app clone"}
        return configs

    def get_configs_as_json(self):
        configs = self.get_configs()
        s = json.dumps(configs)
        return s

def get_constellation_data(user_or_domain, constellation):
    def _domain(user_or_domain):
        domain = user_or_domain
        if user_or_domain.find('@') > 0:
            domain = user_or_domain.split('@')[1]
        return domain

    try:
        
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/"+constellation
        s = red.get(redis_key)
        data = json.loads(s)
        return data
    except:
        return None    
