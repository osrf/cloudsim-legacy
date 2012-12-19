from __future__ import with_statement
from __future__ import print_function

import sys
import os
import unittest

import json
from testing import get_test_runner 
import commands
 
class RedisPublisher(object):
    def __init__(self, username):
        self.username = username
        self.channel_name = self.username.split("@")[1]
        try:
            import redis
            self.redis_cli = redis.Redis()
        except:
            print("warning, redis not installed")
        
        
    def event(self, data):
        prefix = ""
        try:
            message = json.dumps(data)
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
    unittest.main(testRunner = get_runner())          
 
