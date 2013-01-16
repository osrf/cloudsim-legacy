from __future__ import print_function
import unittest
import time
import logging
from common import testing
import json

def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launch", msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
  



def _domain(user_or_domain):
    domain = user_or_domain
    if user_or_domain.find('@') > 0:
        domain = user_or_domain.split('@')[1]
    return domain


  
def set_constellation_data(user_or_domain, constellation, value, expiration = None):
    try:
        import redis
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/" + constellation
        
        str = json.dumps(value)
        red.set(redis_key, str)
        if expiration:
            red.expire(redis_key, expiration)
    except Exception, e:
        log("can't set constellation data: %s" % e)
        

def get_constellation_data(user_or_domain, constellation):
    try:
        import redis
        red = redis.Redis()
        domain = _domain(user_or_domain)
        redis_key = domain+"/"+constellation
        str = red.get(redis_key)
        data = json.loads(str)
        return data
    except:
        return None    

class RedisPublisher(object):
    def __init__(self, username, tags):
        self.username = username
        self.tags = tags
        self.channel_name = self.username.split("@")[1]
        try:
            import redis
            self.redis_cli = redis.Redis()
        except:
            print("warning, redis not installed")
        
        
    def event(self, data):
        prefix = ""
        try:
            all_data = {}
            all_data.update(self.tags)
            all_data.update(data)
            message = json.dumps(all_data)
            self.redis_cli.publish(self.channel_name, message)
        except:
            prefix = "[redis not installed] "
            
        print("%s%s" %(prefix, message ) )
        
class TestMach(object):
    
    def __init__(self, event):
        self.event = event
        
    def publish(self, data):
        self._event( data)
    
    def _event(self, event_data):    
        self.event( event_data)

class PublishTest(unittest.TestCase): 
    
    def test_one(self):
        
        redis_pub = RedisPublisher("toto@toto.com")
        
        m2 = TestMach(redis_pub.event)
        m2.publish( {'data':3})

def subscribe(channels):
    import redis
    redis_client = redis.Redis()
    ps = redis_client.pubsub()
    ps.subscribe(channels)
    for e in ps.listen():
        print(e)
    
        

             
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main(testRunner = testing.get_test_runner())