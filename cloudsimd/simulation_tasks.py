from __future__ import print_function

import redis
import unittest
import launchers.launch_utils.launch_db as launch_db
import launchers.launch_utils.launch as launch


def log(msg, channel = "tasks"):
    try:
        r = redis.Redis()
        r.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)
  

def _find_task(tasks, task_id):
    for task in tasks:
        if task['task_id'] == task_id:
            return task
    return None

def create_task(constellation_name, 
                    task_title, ros_package, ros_launch, 
                    timeout,
                    ros_args, latency, data_cap):
    
    cs = launch_db.ConstellationState(constellation_name)
    tasks = cs.get_value('tasks')
    
    task_id = "t" + launch.get_unique_short_name()
    
    task = {'task_id' : task_id,
            'task_state' : 'not started',
            'task_title': task_title, 
            'ros_package': ros_package,
            'ros_launch': ros_launch,
            'timeout' : timeout,
            'ros_args' : ros_args,
            'latency':latency,
            'data_cap' : max_data}
    tasks.append(task)
    
    cs.set_value('tasks', tasks)
     


def update_task(constellation_name, task_id, 
                      task_title, 
                      ros_package, 
                      ros_launch, 
                      timeout,
                      ros_args, 
                      latency, 
                      data_cap,):

    log("update_task %s/%s" % (constellation_name, task_id))

    cs = launch_db.ConstellationState(constellation_name)
    tasks = cs.get_value('tasks')
    
    task = _find_task(tasks, task_id)
    task['task_title'] = task_title
    task['ros_package'] = ros_package
    task['ros_launch'] = ros_launch
    task['ros_args'] = ros_args
    task['latency'] = latency
    task['task_state'] = task_state
    task['timeout'] = timeout
    task['data_cap'] = data_cap
    
def delete_task(constellation_name, task_id):
    log("delete_task %s/%s" % (constellation_name, task_id))
    cs = launch_db.ConstellationState(constellation_name)
    tasks = cs.get_value('tasks')
    task = _find_task(tasks, task_id)
    tasks.remove(task)
    cs.set_value("tasks", tasks)

def start_task(constellation_name, task_id):
    log("start_task %s/%s" % (constellation_name, task_id))
    cs = launch_db.ConstellationState(constellation_name)
    task_state = cs.get_value('task_state')
    if task_state == "ready":
        tasks = cs.get_value('tasks')
        task = _find_task(tasks, task_id)
        cs.set_value("task_state", "starting %s" % task_id)
        # start gazebo
        # start traffic shaper
        
    
def stop_task(constellation_name, task_id):
    log("stop_task %s/%s" % (constellation_name, task_id))
    cs = launch_db.ConstellationState(constellation_name)
    task_state = cs.get_value('task_state')
    if task_state  == "running %s" % task_id:
        # stop gazebo
        # stop traffic shaper
        cs.set_value("task_state", "stopping %s" % task_id)
        
         
    

class TaskCase(unittest.TestCase):
    def test_task(self):
        print("ho")
        r.set('tests/tasky', '{"tasks":[]}')
        

if __name__ == "__main__":
    unittest.main()