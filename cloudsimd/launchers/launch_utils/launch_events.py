from __future__ import print_function
from launch_db import log, publish_event


def simulator_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event("simulator", username, msg)

def gl_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event("gl",username, msg)

def latency_event(username, configuration, constellation_name, machine_name, mini, avg, maxi, mdev ):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 
           'min': mini, 'avg' : avg, 'max':maxi, 'mdev':mdev}
    publish_event("latency", username, msg)

def machine_state_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event("machine", username, msg)

def launch_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event("launch", username, msg)


