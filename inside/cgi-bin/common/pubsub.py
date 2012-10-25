from __future__ import with_statement
from __future__ import print_function

import sys
import os
import redis
import unittest

import json

from machine import Machine2, StdoutPublisher
import commands
from machine_configuration import Machine_configuration

class RedisPublisher(object):
    def __init__(self, username):
        self.username = username
        self.redis_cli = redis.Redis()
        self.channel_name = self.username.split("@")[1]
        
    def event(self, data):
        message = json.dumps(data)
        self.redis_cli.publish(self.channel_name, message)
        print("%s" %(message ) )
        
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
    redis_client = redis.Redis()
    ps = redis_client.pubsub()
    ps.subscribe(channels)
    for e in ps.listen():
        print(e)
    
        
class TestMachinePub(unittest.TestCase):
    
    def get_boto_path(self):
        return "../../../../boto.ini"
            
    def test_redis_1(self):
        
            
        root_directory = "test_pubsub"
        publisher = RedisPublisher("toto@toto.com")
        machine_name = "pubsub"
        
        cmd = "rm -rf %s" % root_directory
        status, o = commands.getstatusoutput(cmd)
        print(o)
        
        startup_script = "#!/bin/bash\necho done > /home/ubuntu/startup.txt\n"
              
        tags = {'pubsub':'test_redis_1', 'user':'toto@toto.com'}
                   
        config = Machine_configuration()
        config.initialize(   image_id ="ami-137bcf7a", 
                             instance_type = 't1.micro', # 'm1.small' , 
                             security_groups = ['ping_ssh'],
                             username = 'ubuntu', 
                             distro = 'precise',
                             startup_script = startup_script,
                             ip_retries=100, 
                             ssh_retries=200)

        machine = Machine2(machine_name,
                         config,
                         publisher.event,
                         tags,
                         credentials_ec2 =  self.get_boto_path(), # boto file
                         root_directory = root_directory)
        
        machine.create_ssh_connect_script()
        
        print("Waiting for ssh")
        machine.ssh_wait_for_ready("/home/ubuntu")
        
        print("Waiting for setup to complete")
        machine.ssh_wait_for_ready()
        
        
    def test_redis_2(self):
        root_directory = "test_pubsub"
        
        id = os.listdir(root_directory)[0]
        config_path = os.path.join(root_directory, id, "instance.json")
        print("machine %s" % config_path)
        self.assert_(os.path.exists(config_path), "no machine")
        
        
        publisher = RedisPublisher("toto@toto.com")# StdoutPublisher("toto@toto.com")
        machine = Machine2.from_file(config_path, publisher.event)

                
        repeats = 3
        for i in range(repeats):
            print("Checking status [%s / %s]" % (i+1, repeats))
            
            m =  machine.test_aws_status()
            print("    aws status= %s" % m)
            try:
                p = machine.ping()
                print("    ping= %s" % str(p) )
            except Exception, e:
                print("    ",e)
            x = machine.test_X()
            print("    X= %s" % x)
            g = machine.test_gazebo()
            print("    gazebo= %s" % g)
              
        print("Shuting down\n\n\n")      
        machine.terminate()
        print("\n\n\n")
        sys.stdout.flush()
             
        
if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main()        
 
