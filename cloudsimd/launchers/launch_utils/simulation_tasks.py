from __future__ import print_function
import time
import redis
import unittest
import  launch_utils.launch_db as launch_db
from launch_utils.launch import get_unique_short_name


r = redis.Redis()

def _find_task(tasks, task_id):
    for task in tasks:
        if task['task_id'] == task_id:
            return task
    return None

def create_task(constellation_name, 
                    task_title, ros_package, ros_launch, ros_args, latency):
    cs = launch_db.ConstellationState(constellation_name)
    tasks = cs.get_value('tasks')
    
    task_id = "t" + get_unique_short_name()
    
    task = {'task_id' : task_id,
            'task_title': task_title, 
            'ros_package': ros_package,
            'ros_launch': ros_launch,
            'ros_args' : ros_args,
            'latency':latency}
    tasks.append(task)
    
    cs.set_value(constellation_name, tasks)
     


def update_task(constellation_name, task_id, 
                      task_title, ros_package, ros_launch, ros_args, latency):
    cs = launch_db.ConstellationState(constellation_name)
    tasks = cs.get_value('tasks')
    
    task = 
    
def delete_task(constellation_name, task_id):
    pass

def start_task(constellation_name, task_id):
    pass

def stop_task(constellation_name, task_id):
    pass


class TaskCase(unittest.TestCase):
    def test_task(self):
        print("ho")
        
        r.set('tests/tasky', '{"tasks":[]}')
        

if __name__ == "__main__":
    unittest.main()