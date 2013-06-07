#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgitb
import json
import redis
import collections

from common import UserDatabase


cgitb.enable()


def log(msg):
    red = redis.Redis()
    red.publish("cloudsim_log",msg)


from common import  authorize, ConfigsDb

email = authorize("officer")




print('Content-type: application/json')
print('\n')

cdb = ConfigsDb(email)

admin_configs = ['vpc_micro_trio',] # 'cloudsim', ]


configs = cdb.get_configs()
udb = UserDatabase()

if not udb.has_role(email, "admin"):
    for name in configs.keys():
        if name.find("nightly") > 0:
            del(configs[name])
        if name.find("nvidia") > 0:
            del(configs[name])

#     for bad_config in admin_configs:
#         if bad_config in configs:
#             del(configs[bad_config]) # remove it
#             log("configs removing %s =  %s" % (bad_config, len(configs) ) )

#s = json.dumps(configs)

od = collections.OrderedDict(sorted(configs.items()))
s = json.dumps(od)
print(s)