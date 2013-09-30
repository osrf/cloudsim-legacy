import requests
import urllib2

import time

# http://docs.python-requests.org/en/latest/

class CloudSimRestApi(object):

    def __init__(self, url, user, passwd):
        self.url = "http://%s" % url
        self.user = user
        self.passwd = passwd

    def _api_get(self, path):
        theurl = "/".join([self.url, path])
        r = requests.get(theurl, auth=(self.user, self.passwd))
        if r.status_code != 200:
            raise Exception("GET request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_post(self, path):
        theurl = "/".join([self.url, path])
        r = requests.post(theurl, auth=(self.user, self.passwd))
        if r.status_code != 200:
            raise Exception("GET request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_put(self, path):
        theurl = "/".join([self.url, path])
        r = requests.put(theurl, auth=(self.user, self.passwd))
        if r.status_code != 200:
            raise Exception("GET request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_delete(self, path):
        theurl = "/".join([self.url, path])
        r = requests.delete(theurl, auth=(self.user, self.passwd))
        if r.status_code != 200:
            raise Exception("GET request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def get_constellations(self):
        cs = self._api_get('cloudsim/inside/cgi-bin/constellations')
        valids = [x for x in cs if 'configuration' in x]
        return valids

    def list_constellations(self):
        constellations = self.get_constellations()
        r = [[x['constellation_name'], x['configuration']]\
              for x in constellations]
        return r

    def get_constellation(self, constellation_name):
        constellations = self.get_constellations()
        for c in constellations:
            if c['constellation_name'] == constellation_name:
                return c
        raise Exception('constellation "%s" not found' % constellation_name)

    def launch_constellation(self, provider, configuration):
        p = urllib2.quote(provider)
        c = urllib2.quote(configuration)
        url = '/cloudsim/inside/cgi-bin/constellations?cloud_provider=' + p
        url += '&configuration=' + c;
        s = self._api_post(url)
        return s

    def update_constellation(self, constellation_name):
        url = '/cloudsim/inside/cgi-bin/constellations';
        url += '/' + constellation_name;
        s = self._api_put(url)
        return s
    
    def terminate_constellation(self, constellation_name):
        url = '/cloudsim/inside/cgi-bin/constellations';
        url += '/' + constellation_name;
        s = self._api_delete(url)
        return s 


def baby_cloudsims(papa_cloudsim, user):
    
    constellations  = papa_cloudsim.get_constellations()
    cloudsims = [c for c in constellations \
                  if c['configuration'].startswith('CloudSim')]
    babies = []
    for cloudsim in cloudsims:
        url = cloudsim['simulation_ip']
        passwd = 'admin' + cloudsim['constellation_name']
        # print("url: http://%s user: %s, psswd: %s" % (url, user, passwd))
        cloudsim = CloudSimRestApi(url, user, passwd)
        babies.append(cloudsim)
    return babies
     
     
def baby_launch(cloudsims, provider, configuration, delay=0.1):
    print("launching %s on %s cloudsims with %s sec delay" % (
                                   configuration, len(cloudsims), delay))
    for cloudsim in cloudsims:
        print("- launching from %s" % cloudsim)
        s = cloudsim.launch_constellation(provider, configuration)
        time.sleep(delay)


def multi_launch(papa, provider, configuration, count, delay=10):
    print("launching %s %s on %s with %s sec delay" % (
                                   count, configuration, papa.url, delay))
    for i in range(count):
        print (" launching %s" % i)
        papa.launch_constellation(provider, configuration)
        time.sleep(delay)
    

def launch_baby_cloudsims(url, papa_name, count=25, user='admin', delay=10):
    papa = CloudSimRestApi(url, user, 'admin%s' % papa_name)
    multi_launch(papa, 'aws', 'CloudSim-stable', count=count, delay=delay)    


def launch_simulators(papa_url, papa_name, user='admin', delay=0.1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    cloudsims = baby_cloudsims(papa, user=user)
    baby_launch(cloudsims, 'aws', 'Simulator-stable', delay)


def update_baby_cloudsims(papa_url, papa_name, user='admin', delay=0.1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    constellations  = papa.get_constellations()
    cloudsims = [c for c in constellations \
                  if c['configuration'].startswith('CloudSim')]
    for cloudsim in cloudsims:
	cloudsim_name = cloudsim['constellation_name']
        print ("updating %s" % cloudsim_name)
        papa.update_constellation(cloudsim_name)


def terminate_baby_cloudsims(papa_url, papa_name, user='admin', delay=0.1):
    papa = CloudSimRestApi(papa_url, user, 'admin%s' % papa_name)
    constellations  = papa.get_constellations()
    cloudsims = [c for c in constellations \
                  if c['configuration'].startswith('CloudSim')]
    for cloudsim in cloudsims:
	cloudsim_name = cloudsim['constellation_name']
        print ("terminating %s" % cloudsim_name)
        papa.terminate_constellation(cloudsim_name)

def update_simulators():
    pass


