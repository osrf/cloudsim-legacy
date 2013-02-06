#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import redis
from common import UserDatabase

cgitb.enable()


def log(msg):
    red = redis.Redis()
    red.publish("cloudsim_log",msg)


from common import  authorize, ConfigsDb

email = authorize()

udb = UserDatabase()
is_admin = udb.is_admin(email)

print('Content-type: application/json')
print('\n')

cdb = ConfigsDb(email)

admin_configs = ['vpc_micro_trio', # 'cloudsim', 
                'micro_vpn',
                'drc_sim_ami']

configs = cdb.get_configs()

if not is_admin:
    for bad_config in admin_configs:
        if bad_config in configs:
            del(configs[bad_config]) # remove it
            log("configs removing %s =  %s" % (bad_config, len(configs) ) )
            

str = json.dumps(configs)
    



print(str)