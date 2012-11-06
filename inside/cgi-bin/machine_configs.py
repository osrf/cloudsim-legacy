#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
cgitb.enable()

from common import  authorize, ConfigsDb

email = authorize()



print('Content-type: application/json')
print('\n')


cdb = ConfigsDb(email)
configs = cdb.get_configs_as_json()

print(configs)