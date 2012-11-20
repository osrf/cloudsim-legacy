#!/usr/bin/env python

from __future__ import with_statement
from __future__ import print_function
import cgi
import cgitb
import json
cgitb.enable()

from common import  authorize, UserDatabase

email = authorize("admin")


print('Content-type: application/json')
print("\n")

db = UserDatabase()
users = db.get_users()
jusers = json.dumps(users)

print(jusers)