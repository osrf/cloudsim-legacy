#!/usr/bin/env python

"""
Update Redis with a new set of VRC tasks for a simulator
"""

import argparse
import redis
import json
import os


def update_redis_tasks(json_file):
    '''
    Read the tasks contained in a JSON file and update Redis
    @param json_file The file with the task definition
    '''
    db = redis.Redis()

    with open(json_file) as f:
        tasks = json.load(f)

        # The tasks are registered using Redis pub service
        for task in tasks:
            db.publish('cloudsim_cmds', json.dumps(task))

    # Remove the tasks file
    os.remove(json_file)


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
