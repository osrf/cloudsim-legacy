import requests
import urllib2

import time

# http://docs.python-requests.org/en/latest/

class CloudSimRestApi(object):
    """
    This class allows to control a cloudsim instance from its rest api.
    It assumes that the CloudSim uses the Basic Auth mechanism.
    """

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

#     def list_constellations(self):
#         """
#         Returns the names and configuration of the constellations.
#         """
#         constellations = self.get_constellations()
#         r = [[x['constellation_name'], x['configuration']]\
#               for x in constellations]
#         return r

    def select_constellations(self, config_start=None):
        """
        Returns the names of constellations. If config is not None, only
        the constellations of this configuration are returned.
        startswith is used for the match, allowing to select "Cloudsim" 
        and "Cloudsim-stabe" together by specifying only "Cloudsim". 
        No regex (yet), please
        """
        constellations = []
        for constellation in self.get_constellations():
            name = constellation['constellation_name']
            const_config = constellation['configuration']
            if config and config.startswith(config_start):
                constellations.append(constellation)
        return constellations

    def get_constellation_data(self, constellation_name):
        """
        returns the data for a specific constellation
        """
        constellations = self.get_constellations()
        for c in constellations:
            if c['constellation_name'] == constellation_name:
                return c
        raise Exception('constellation "%s" not found' % constellation_name)

    def launch_constellation(self, provider, configuration):
        """
        Creates a new constellation with tbe specified configuration
        """
        p = urllib2.quote(provider)
        c = urllib2.quote(configuration)
        url = '/cloudsim/inside/cgi-bin/constellations?cloud_provider=' + p
        url += '&configuration=' + c;
        s = self._api_post(url)
        return s

    def update_constellation(self, constellation_name):
        """
        Updates a constellation
        """
        url = '/cloudsim/inside/cgi-bin/constellations';
        url += '/' + constellation_name;
        s = self._api_put(url)
        return s
    
    def terminate_constellation(self, constellation_name):
        """
        Terminates a constellation
        """
        url = '/cloudsim/inside/cgi-bin/constellations';
        url += '/' + constellation_name;
        s = self._api_delete(url)
        return s


def update_children(cloudsim, config=None, delay=10):
    """
    Updates all constellations for a CloudSimRestApi instance. If config is
    not None, the update only applies to the selected configuration (i.e 
    "Simulator" or "Cloudsim". No regex, please
    """
    constellations = cloudsim.select_constellations(cloudsim, config)
    for constellation in constellations:
        name = constellation['constellation_name']
        print ("updating %s" % name)
        cloudsim.update_constellation(name)
        time.sleep(delay)


def terminate_children(cloudsim, config=None, delay=1):
    """
    Terminates all constellations of a CloudSimRestApi instance, unless a 
    specific configuration is requested (see update_children)
    """
    constellations_data = cloudsim.select_constellations(cloudsim, config)
    for constellation in constellations_data:
        name = constellation['constellation_name']
        print ("terminating %s" % name)
        cloudsim.terminate_constellation(name)
        time.sleep(delay)


def multi_launch(papa, provider, configuration, count, delay=10):
    """
    Launches multiple constellations of the specified configuration
    inside a the CloudsimRestApi papa. 
    This can be used used to launch "baby CloudSims"
    """
    print("launching %s %s on %s with %s sec delay" % (
                                   count, configuration, papa.url, delay))
    for i in range(count):
        print (" launching %s" % i)
        papa.launch_constellation(provider, configuration)
        time.sleep(delay)
     
     
def baby_launch(cloudsims, provider, configuration, delay=0.1):
    """
    Launches a constellation of specific configuration for each 
    CloudSimRestApi in the cloudsims list.
    This can be used to launch simulators inside "baby CloudSims"
    """
    print("launching %s on %s cloudsims with %s sec delay" % (
                                   configuration, len(cloudsims), delay))
    for cloudsim in cloudsims:
        print("- launching from %s" % cloudsim)
        s = cloudsim.launch_constellation(provider, configuration)
        time.sleep(delay)

