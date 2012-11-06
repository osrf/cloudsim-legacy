#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
cgitb.enable()

from common import  authorize, MachineDb

email = authorize()


print('Content-type: application/json')
print("\n")


mdb = MachineDb(email)
machines = mdb.get_machines_as_json()

print(machines)