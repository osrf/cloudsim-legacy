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
        configs['vpc_trio_prerelease'] = {'description': "3 machines for the VRC competition: a GPU field computer, a router and a GPU simulator, using gazebo and drcsim pre-release packages"} 
        configs['vpc_micro_trio'] = {'description': "3 micro instances for testing constellations: field computer, router and simulator"} 
        configs['vpc_trio'] = {'description': "3 machines for the VRC competition: a GPU field computer, a router and a GPU simulator, using gazebo and drcsim packages"}
        configs['simulator'] = {'description': "1 machine for using gzserver on the cloud: GPU computer with the latest ros-fuerte, gazebo and drcsim packages installed"}
        configs['simulator_prerelease'] = {'description': "1 machine for using gzserver on the cloud: GPU computer with the latest ros-fuerte, gazebo and drcsim pre-release packages installed"}
        configs['cloudsim'] = {'description': "1 machine for starting a CloudSim on the cloud: A micro instance web app clone"}
        
        configs['vrc_constellation'] = {'description': "4 machines: a simulator, a router and two field computers"}
        
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
        redis_key = "cloudsim/"+constellation
        s = red.get(redis_key)
        
        data = json.loads(s)
        domain_data = _domain(data['username'])
        
        if domain != domain_data:
            return None
        
        return data
    except:
        return None    
