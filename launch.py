#!/usr/bin/env python
from __future__ import print_function
import sys
import os

daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'cloudsimd'))
sys.path.insert(0, daemon_path)
print(daemon_path)

from cloudsimd import launch_constellation

print (sys.argv)

username = sys.argv[1]
configuration = sys.argv[2]

count = 1
if len(sys.argv) > 3:
    count = int(sys.argv[3])

launch_constellation(username, configuration, count)




