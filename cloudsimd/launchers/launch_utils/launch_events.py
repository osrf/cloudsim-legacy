from __future__ import print_function
from launch_db import log, publish_event


def simulator_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event(username, "simulator", msg)

def gl_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event(username, "gl", msg)

def latency_event(username, configuration, constellation_name, machine_name, mini, avg, maxi, mdev ):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 
           'min': mini, 'avg' : avg, 'max':maxi, 'mdev':mdev}
    publish_event(username, "latency",  msg)

def machine_state_event(username, configuration, constellation_name, machine_name, data):
    msg = {'configuration':configuration, 'constellation_name':constellation_name, 'machine_name': machine_name, 'data': data}
    publish_event(username, "machine", msg)

def launch_event(username, configuration, constellation_name, machine_name, color, text):
    msg = {'configuration':configuration, 
           'constellation_name':constellation_name, 
           'machine_name': machine_name, 
           'color': color, 
           'text': text}
    publish_event(username, "launch", msg)


