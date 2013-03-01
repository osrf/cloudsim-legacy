from __future__ import print_function
import unittest
import logging
import testing
import json

import redis


def log(msg, channel = "launch"):
    try:
        
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
  

def publish_event(username, type, data):
    msg = {}
    msg.update(data)
    msg['type'] = type
    msg['username'] = username
    try:
        
        redis_cli = redis.Redis()
        channel_name = msg['username'].split("@")[1]
        j_msg = json.dumps(msg)
        redis_cli.publish(channel_name, j_msg)
    except Exception, e:
        log("publish_event: [%s] type %s msg[%s]" % (username, type, msg))
        
            
class ConstellationState(object):
    
    def __init__(self, username, constellation_name):
        self.username = username
        self.constellation_name = constellation_name
        
    def has_value(self, name):
        resources = get_constellation_data(self.username,  self.constellation_name)
        return resources.has_key(name)
        
    def get_value(self, name):
        resources = get_constellation_data(self.username,  self.constellation_name)
        return resources[name]
    
    def set_value(self, name, value):
        resources = get_constellation_data(self.username,  self.constellation_name)
        if not resources:
            resources = {}
        resources[name] = value
        expiration = None
        set_constellation_data(self.username, self.constellation_name, resources, expiration)
    
    def expire(self, nb_of_secs):
        resources  = get_constellation_data(self.username,  self.constellation_name)
        set_constellation_data(self.username, self.constellation_name, resources, nb_of_secs)



def _domain(user_or_domain):
    domain = user_or_domain
    if user_or_domain.find('@') > 0:
        domain = user_or_domain.split('@')[1]
    return domain


  
def set_constellation_data(user_or_domain, constellation, value, expiration = None):
    try:
        
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = "cloudsim/"domain+"/" + constellation
        
        s = json.dumps(value)
        red.set(redis_key, s)
        if expiration:
            red.expire(redis_key, expiration)
    except Exception, e:
        log("can't set constellation data: %s" % e)
        

def get_constellations():
    try:
        data = []
        
        red = redis.Redis()
        keys = red.keys("*")
        for key in keys:
            toks = key.split("/")
            if len(toks) == 3:
                domain = toks[1]
                constellation = toks[2]
                data.append( (domain, constellation) )
        return data
    except:
        return None        

def get_constellation_data(user_or_domain, constellation):
    try:
        
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/"+constellation
        s = red.get(redis_key)
        data = json.loads(s)
        return data
    except:
        return None    

__CONFIG__KEY__ = "cloudsim_config"

def set_cloudsim_config(config):
    
    r = redis.Redis()
    s = json.dumps(config)
    r.set(__CONFIG__KEY__, s)
    
def get_cloudsim_config():
    
    r = redis.Redis()
    s = r.get(__CONFIG__KEY__)
    config = json.loads(s)
    return config


def subscribe(channels):
    
    redis_client = redis.Redis()
    ps = redis_client.pubsub()
    ps.subscribe(channels)
    for e in ps.listen():
        print(e)
    
        

             
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main(testRunner = testing.get_test_runner())