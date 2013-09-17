import json
import redis


def get_cloudsim_configuration_list():
    r = redis.Redis()
    s = r.get("cloudsim_configuration_list")
    configs = json.loads(s)
    return configs

class ConfigsDb(object):
    def __init__(self, email):
        self.user = email
         
        
    def get_config_dir(self):
        return self.configs_dir
    
    
    def get_configs(self):
        configs = get_cloudsim_configuration_list()
        return configs

    def get_configs_as_json(self):
        configs = self.get_configs()
        s = json.dumps(configs)
        return s

def get_constellation_data(user_or_domain, constellation):
        red = redis.Redis()
        redis_key = "cloudsim/"+constellation
        s = red.get(redis_key)
        
        data = json.loads(s)
        
        return data

