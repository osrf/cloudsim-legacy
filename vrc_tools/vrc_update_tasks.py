#!/usr/bin/env python

"""
Update Redis with a new set of VRC tasks
"""

import argparse
import redis
import json


def update_redis_tasks(json_file):
    db = redis.Redis()

    with open(json_file) as f:
        tasks = json.load(f)
        #json_tasks = json.dumps(tasks)

        for task in tasks:
            db.publish('cloudsim_cmds', json.dumps(task))

if __name__ == '__main__':

    # Specify command line arguments
    parser = argparse.ArgumentParser(
        description=('Update Redis with new tasks'))

    parser.add_argument('json_file', help='JSON file containing the tasks')

    # Parse command line arguments
    args = parser.parse_args()
    arg_json_file = args.json_file

    # Feed Redis with the tasks. Yummy!
    update_redis_tasks(arg_json_file)
