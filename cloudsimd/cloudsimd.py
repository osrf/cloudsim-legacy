#!/usr/bin/python

import time
import redis


# sudo initctl reload-configuration
# sudo start script



r = redis.Redis()
inc = 0
while True:
    inc +=1
    time.sleep(1)
    r.publish("osrfoundation.org", "{'type': 'test_msg', 'count':%s}" % inc)
    
    