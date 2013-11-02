from cloudsim_rest_api import CloudSimRestApi
from cloudsim_rest_api import multi_launch
from cloudsim_rest_api import launch_for_each_cloudsim
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
    

def launch_baby_cloudsims(url, papa_name, count=1, user='admin', delay=10):
    """
    Creates many Cloudsims for a papa cloudsim. It is good practice to wait
    between calls to avoid network clogging.
    """
    papa = CloudSimRestApi(url, user, 'admin%s' % papa_name)
    multi_launch(papa, 'aws', 'CloudSim-stable', count=count, delay=delay)    


def launch_simulators(papa_url, papa_name, user='admin', delay=0.1):
    """
    Create a simulator-stable constellation for each Cloudsim.
    """
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    cloudsims = get_baby_cloudsims(papa, user=user)
    launch_for_each_cloudsim(cloudsims, 'aws', 'Simulator-stable', delay)


def update_baby_cloudsims(papa_url, papa_name, user='admin', delay=10):
    """
    Udates each baby CloudSim. 
    """
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    update_children(papa, config="CloudSim")


def terminate_cloudsims(papa_url, papa_name, user='admin', delay=0.1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    terminate_children(papa, config='CloudSim', delay=delay)


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
    cloudsims = papa.select_constellations("Cloudsim")
    for data in cloudsims:
        url = data['simulation_ip']
        name = data['constellation_name'].replace('admin','')
        cloudsim = CloudSimRestApi(url, user, 'admin%s' % name)
        terminate_children(cloudsim, config="Simulator", delay=delay)


if __name__ == "__main__":
    
    #
    # This is only a test.
    # 
    step = 3

    if step == 1:
        # launch a cloudsim
        grandpa_cloudsim = CloudSimRestApi('localhost', 'admin', 'admin')
        grandpa_cloudsim.launch_constellation("aws", "CloudSim-stable")
        # now wait for it...
        
    papa_url='54.237.100.112'
    papa_name = 'cxae030230'
    user = 'admin'
    delay = 10
    
    if step == 2:
        count = 1
        launch_baby_cloudsims(papa_url, papa_name, count, user, delay)

# TO DO    
#    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)   
#    update_baby_cloudsims(papa_url, papa_name)

    
    if step == 3:
        delay = 1
        terminate_cloudsims(papa_url, papa_name, user, delay)
    
