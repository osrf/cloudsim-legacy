#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import os
import redis
from json import loads


redis_client = redis.Redis()


def run():
    channels = ["cloudsim_log", "cloudsim_cmds"] 
    #channels.append("osrfoundation.org")
    
    ps = redis_client.pubsub()
    ps.subscribe(channels)
    
    for msg in ps.listen():
        print(msg) 
        try:
            data = loads(msg['data'])
            print ("\nDATA\n%s\n" % data)
        except:
            print("NO DATA")

run()
