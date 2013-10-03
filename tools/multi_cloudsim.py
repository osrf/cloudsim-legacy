
from cloudsim_rest_api import CloudSimRestApi
from cloudsim_rest_api import multi_launch
from cloudsim_rest_api import baby_launch
from cloudsim_rest_api import update_children
from cloudsim_rest_api import terminate_children

"""
Constellations management tools over the REST API

These functions assume that an admin user "admin" with a passwd 
    adminxxxx exists (where xxxx is the constellation name).
"""

def get_baby_cloudsims(papa_cloudsim, user):
    """
    Returns a list of CloudSimRestApi for each "baby CloudSim".
    """
    
    cloudsims  = papa_cloudsim.select_constellations("CloudSim")
    babies = []
    for cloudsim in cloudsims:
        url = cloudsim['simulation_ip']
        passwd = 'admin' + cloudsim['constellation_name']
        # print("url: http://%s user: %s, psswd: %s" % (url, user, passwd))
        cloudsim = CloudSimRestApi(url, user, passwd)
        babies.append(cloudsim)
    return babies
    

def launch_baby_cloudsims(url, papa_name, count=25, user='admin', delay=10):
    """
    Creates many Cloudsims for a pap cloudsim. It is good practice to wait
    between calls to avoid network clogging.
    """
    papa = CloudSimRestApi(url, user, 'admin%s' % papa_name)
    multi_launch(papa, 'aws', 'CloudSim-stable', count=count, delay=delay)    


def launch_simulators(papa_url, papa_name, user='admin', delay=0.1):
    """
    Create a simulator-stable constellation for each Cloudsim
    """
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    cloudsims = get_baby_cloudsims(papa, user=user)
    baby_launch(cloudsims, 'aws', 'Simulator-stable', delay)


def update_baby_cloudsims(papa_url, papa_name, user='admin', delay=10):
    """
    Udates each baby CloudSim. 
    """
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    update_children(papa)


def terminate_cloudsims(papa_url, papa_name, user='admin', delay=0.1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    terminate_children(papa, delay)


def update_simulators(papa_url, papa_name, user='admin', delay=10):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    cloudsims = papa.select_constellations("Cloudsim")
    for data in cloudsims:
        name = data['constellation_name']
        url = data['simulation_ip']
        cloudsim = CloudSimRestApi(url, user, 'admin%s' % name)
        update_children(cloudsim, config="Simulator", delay=delay)


def terminate_simulators(papa_url, papa_name, user='admin', delay=1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    constellations  = papa.get_constellations()
    cloudsims_data = [c for c in constellations \
                  if c['configuration'].startswith('CloudSim')]
    
    for data in cloudsims_data:
        url = data['simulation_ip']
        name = data['constellation_name'].replace('admin','')
        cloudsim = CloudSimRestApi(url, user, 'admin%s' % name)
        terminate_children(cloudsim, delay=delay)


