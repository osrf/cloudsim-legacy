#!/usr/bin/env python

"""
Update Redis with a new set of VRC tasks for a simulator
"""

import argparse
import redis
import json
import time
import sys

sys.path.append('/var/www/cloudsimd')
import cloudsimd

MAX_WAIT = 20.0

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
            try:
                old_num_tasks = len(cloudsimd.ConstellationState(cloudsimd.get_constellation_names()[0]).get_value('tasks'))
                db.publish('cloudsim_cmds', json.dumps(task))
                # Wait for the new task to appear (to avoid out-of-order insertion
                # due to the asynchronous processing in cloudsimd)
                start = time.time()
                while old_num_tasks == len(cloudsimd.ConstellationState(cloudsimd.get_constellation_names()[0]).get_value('tasks')):
                    time.sleep(0.25)
                    if (time.time() - start) > MAX_WAIT:
                        raise Exception('timeout')
            except Exception as e:
                print 'Failed to add task %s: %s'%(task, e)

    # Remove the tasks file
    #os.remove(json_file)


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
