from __future__ import print_function
import unittest
import logging
import testing
import json
import time
import redis


def log(msg, channel="launch_db"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
        print("launch_db>", msg)
    except:
        print("Warning: redis not installed.")
    #print("cloudsim log> %s" % msg)


def publish_event(username, type, data):
    msg = {}
    msg.update(data)
    msg['type'] = type
    msg['username'] = username
    try:
        redis_cli = redis.Redis()
        channel_name = msg['username'].split("@")[1]
        j_msg = json.dumps(msg)
        redis_cli.publish(channel_name, j_msg)
    except Exception:
        log("publish_event: [%s] type %s msg[%s]" % (username, type, msg))


class Lock(object):
    # https://chris-lamb.co.uk/posts/distributing-locking-python-and-redis
    def __init__(self, key, expires=120, timeout=90):
        """
        Distributed locking using Redis SETNX and GETSET.

        Usage::

            with Lock('my_lock'):
                print "Critical section"

        :param  expires     We consider any existing lock older than
                            ``expires`` seconds to be invalid in order to
                            detect crashed clients. This value must be higher
                            than it takes the critical section to execute.
        :param  timeout     If another client has already obtained the lock,
                            sleep for a maximum of ``timeout`` seconds before
                            giving up. A value of 0 means we never wait.
        """

        self.r = redis.Redis()
        self.key = key
        self.timeout = timeout
        self.expires = expires

    def __enter__(self):
        timeout = self.timeout
        while timeout >= 0:
            expires = time.time() + self.expires + 1

            if self.r.setnx(self.key, expires):
                # We gained the lock; enter critical section
                return

            current_value = self.r.get(self.key)

            # We found an expired lock and nobody raced us to replacing it
            if current_value and float(current_value) < time.time() and \
               self.r.getset(self.key, expires) == current_value:
                    return

            timeout -= 1
            time.sleep(1)

        raise LockTimeout("Timeout whilst waiting for lock")

    def __exit__(self, exc_type, exc_value, traceback):
        self.r.delete(self.key)


class LockTimeout(BaseException):
    pass


class ConstellationState(object):
    """
    This class is the access point to the constellation information in Redis
    """
    def __init__(self, constellation_name):
        self.constellation_name = constellation_name
        self.my_lock = constellation_name

    def has_value(self, name):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            return name in resources

    def get_value(self, name):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            return resources[name]

    def get_values(self):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            return resources

    def _set_value(self, name, value):
        log("%s/%s = %s " % (self.constellation_name, name, value))
        resources = get_constellation_data(self.constellation_name)
        if not resources:
            resources = {}
        resources[name] = value
        expiration = None
        set_constellation_data(self.constellation_name, resources, expiration)

    def set_value(self, name, value):
        with Lock(self.my_lock):
            self._set_value(name, value)

    def get_task(self, task_id):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            tasks = resources['tasks']
            for task in tasks:
                if task['task_id'] == task_id:
                    return task
            raise KeyError(task_id)

    def get_task_names(self):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            tasks = resources['tasks']
            ids = [task['task_id'] for task in tasks]
            return ids

    def update_task(self, task_id, updated_task):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            tasks = resources['tasks']
            for task in tasks:
                if task['task_id'] == task_id:
                    task.update(updated_task)
                    self._set_value('tasks', tasks)
                    return
            raise KeyError(task_id)

    def update_task_value(self, task_id, key, value):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            tasks = resources['tasks']
            for task in tasks:
                if task['task_id'] == task_id:
                    task[key] = value
                    self._set_value('tasks', tasks)
                    return
            raise KeyError(task_id)    

    def delete_task(self, task_id):
        with Lock(self.my_lock):
            resources = get_constellation_data(self.constellation_name)
            tasks = resources['tasks']
            for task in tasks:
                if task['task_id'] == task_id:
                    tasks.remove(task)
                    self._set_value('tasks', tasks)
                    return
            raise KeyError(task_id)

    def expire(self, nb_of_secs):
        with Lock(self.my_lock):
            log('expiration of %s in %s sec' % (self.constellation_name, nb_of_secs))
            resources = get_constellation_data(self.constellation_name)
            set_constellation_data(self.constellation_name, resources, nb_of_secs)


def _domain(user_or_domain):
    domain = user_or_domain
    if user_or_domain.find('@') > 0:
        domain = user_or_domain.split('@')[1]
    return domain


def set_constellation_data(constellation, value, expiration=None):
    try:

        red = redis.Redis()
        redis_key = "cloudsim/" + constellation

        s = json.dumps(value)
        red.set(redis_key, s)
        if expiration:
            red.expire(redis_key, expiration)
    except Exception, e:
        log("can't set constellation data: %s" % e)


def get_constellation_names():
    try:
        data = []

        red = redis.Redis()
        keys = red.keys("*")
        for key in keys:
            toks = key.split("cloudsim/")
            if len(toks) == 2:
                constellation = toks[1]
                data.append(constellation)
        return data
    except:
        return None


def get_constellation_data(constellation):
    try:

        red = redis.Redis()
        redis_key = "cloudsim/" + constellation
        s = red.get(redis_key)
        data = json.loads(s)
        return data
    except:
        return None

__CONFIG__KEY__ = "cloudsim_config"
__CONFIGURATIONS__KEY__ = "cloudsim_configuration_list"


def set_cloudsim_configuration_list(config_list):
    r = redis.Redis()
    s = json.dumps(config_list)
    r.set(__CONFIGURATIONS__KEY__, s)


def set_cloudsim_config(config):
    r = redis.Redis()
    s = json.dumps(config)
    r.set(__CONFIG__KEY__, s)
    
def get_cloudsim_config():
    r = redis.Redis()
    s = r.get(__CONFIG__KEY__)
    config = json.loads(s)
    return config




if __name__ == '__main__':
    print('Machine TESTS')
    unittest.main(testRunner = testing.get_test_runner())