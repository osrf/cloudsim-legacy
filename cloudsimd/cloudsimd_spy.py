#!/usr/bin/python

from __future__ import with_statement
from __future__ import print_function

import sys
import redis
from json import loads


redis_client = redis.Redis()


def run():
    
    channels = ["cloudsim_log", "cloudsim_cmds"]
    for channel in sys.argv[1:]:
        if channel == 'o':
            channel = 'osrfoundation.org'
        channels.append(channel)
    
    
    #channels.append("osrfoundation.org")
    
    ps = redis_client.pubsub()
    ps.subscribe(channels)
    
    for msg in ps.listen():
        print(msg)
        if msg['channel'] == "cloudsim_cmds":
            try:
                data = loads(msg['data'])
                print ("CMD SPY:msg['data'] \n=============\n%s\n===============\n" % data)
            except:
                print("-")

run()
