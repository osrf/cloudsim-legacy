#!/usr/bin/env python

"""
Remove the current list of tasks from the Redis DB
"""

import argparse
import sys
import os

# Create the basepath of cloudsim
basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, basepath)
from cloudsimd import cloudsimd


def remove_redis_tasks():
    '''
    Remove the current list of tasks
    '''
    cloudsimd.remove_tasks()


if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Remove the current list of tasks'))

    # Parse command line arguments
    args = parser.parse_args()

    remove_redis_tasks()
