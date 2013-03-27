import redis
import json



def get_cloudsim_config():
    """
    Returns the information stored in the cloudsim daemon
    """
    r = redis.Redis()
    s = r.get("cloudsim_config")
    config = json.loads(s)
    return config