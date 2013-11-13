import requests
import urllib2
import time
import urlparse

# this script uses requests
# http://docs.python-requests.org/en/latest/

class CloudSimRestApi(object):
    """
    This class allows to control a cloudsim instance from its rest api.
    It assumes that the CloudSim uses the Basic Auth mechanism.
    """

    def __init__(self, ip, user, passwd):
        """
        Initialization, only pass the ip as the url
        """
        self.url = "http://%s" % ip
        self.user = user
        self.passwd = passwd

    def _api_get(self, url):
        """
        Internal http GET boilerplate
        """
        theurl = urlparse.urljoin(self.url, url)
        r = requests.get(theurl, auth=(self.user, self.passwd))
        if r.status_code != requests.codes.ok:
            raise Exception("GET request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_post(self, url):
        """
        Internal http POST boilerplate
        """
        theurl = urlparse.urljoin(self.url, url)
        r = requests.post(theurl, auth=(self.user, self.passwd))
        if r.status_code != requests.codes.ok:
            raise Exception("POST request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_put(self, url):
        """
        Internal http PUT boilerplate
        """
        theurl = urlparse.urljoin(self.url, url)
        r = requests.put(theurl, auth=(self.user, self.passwd))
        if r.status_code != requests.codes.ok:
            raise Exception("PUT request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _api_delete(self, url):
        """
        Internal http DELETE boilerplate
        """
        theurl = urlparse.urljoin(self.url, url)
        r = requests.delete(theurl, auth=(self.user, self.passwd))
        if r.status_code != requests.codes.ok:
            raise Exception("DELETE request error (code %s)" % r.status_code)
        j = r.json()
        return j

    def _get_query_param_str(self, param_dict):
        """
        Internal function to generate query parameter values for url
        """
        if len(param_dict) == 0:
            return ""

        params = ''
        for k,v in param_dict.iteritems():
            if v not in ['', None]:
                param = urllib2.quote(k)
                val = urllib2.quote("%s" % v)
                params +=  "&%s=%s" % (param, val)
        # replace first & with ?
        r = '?' + params[1:]
        return r

    def get_constellations(self):
        """
        Returns the list of constellations for this CloudSim
        """
        cs = self._api_get('cloudsim/inside/cgi-bin/constellations')
        valids = [x for x in cs if 'configuration' in x]
        return valids

    def select_constellations(self, config=None):
        """
        Returns the names of constellations. If config is not None, only
        the constellations of this configuration are returned.
        startswith is used for the match, allowing to select "Cloudsim" 
        and "Cloudsim-stable" together by specifying only "Cloudsim". 
        No regex (yet), please
        """
        constellations = []
        for constellation in self.get_constellations():
            const_config = constellation['configuration']
            if config and const_config.startswith(config):
                constellations.append(constellation)
        return constellations

    def get_constellation_data(self, constellation_name):
        """
        Returns the data for a specific constellation
        """
        constellations = self.get_constellations()
        for c in constellations:
            if c['constellation_name'] == constellation_name:
                return c
        raise Exception('constellation "%s" not found' % constellation_name)

    def launch_constellation(self, provider, configuration):
        """
        Creates a new constellation with the specified configuration
        """
        p = urllib2.quote(provider)
        c = urllib2.quote(configuration)
        url = '/cloudsim/inside/cgi-bin/constellations'
        url += '?cloud_provider=' + p
        url += '&configuration=' + c;
        s = self._api_post(url)
        return s

    def update_constellation(self, constellation_name):
        """
        Updates a constellation. Returns an error code 
        or the constellation name
        """
        url = urlparse.urljoin('/cloudsim/inside/cgi-bin/constellations/',
                constellation_name)
        s = self._api_put(url)
        return s

    def terminate_constellation(self, constellation_name):
        """
        Terminates a constellation
        """
        url = urlparse.urljoin('/cloudsim/inside/cgi-bin/constellations/',
                                constellation_name)
        s = self._api_delete(url)
        return s

    def create_task(self, constellation_name, task_dict):
        """
        Adds a simulation task
        """
        url = urlparse.urljoin('/cloudsim/inside/cgi-bin/tasks/',
                               constellation_name);
        url += self._get_query_param_str(task_dict)
        r = self._api_post(url)
        return r

    def read_task(self, constellation_name, task_id):
        """
        Returns task information
        """ 
        url = urlparse.urljoin('/cloudsim/inside/cgi-bin/tasks/',
                               constellation_name + '/')
        url = urlparse.urljoin(url, task_id)
        r = self._api_get(url)
        return r

# 
#     def update_task(self, task_dict):
#         pass
# 
#     def delete_task(self):
#         pass

    def start_task(self, constellation_name, task_id):
        """
        Start a simulation task
        """
        url = '/cloudsim/inside/cgi-bin/cloudsim_cmd' 

        param_dict = {'command' : 'start_task', 
                      'constellation' : constellation_name,
                      'task_id' : task_id}
        url += self._get_query_param_str(param_dict)
        r = self._api_get(url)
        return r


    def stop_task(self, constellation_name):
        """
        Stop the running simulation task
        """
        url = '/cloudsim/inside/cgi-bin/cloudsim_cmd' 
        
        param_dict = {'command' : 'stop_task', 
                      'constellation' : constellation_name}
        url += self._get_query_param_str(param_dict)
        r = self._api_get(url)
        return r


def update_children(cloudsim, config=None, delay=10):
    """
    Updates all constellations for a CloudSimRestApi instance. If config is
    not None, the update only applies to the selected configuration (i.e 
    "Simulator" or "Cloudsim". No regex, please
    """
    constellations = cloudsim.select_constellations(config)
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
    constellations_data = cloudsim.select_constellations(config)
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
     
     
def launch_for_each_cloudsim(cloudsims, provider, configuration, delay=0.1):
    """
    Launches a constellation of specific configuration for each 
    CloudSimRestApi in the cloudsims list.
    This can be used to launch simulators inside "baby CloudSims"
    """
    print("launching %s on %s cloudsims with %s sec delay" % (
                                   configuration, len(cloudsims), delay))
    for cloudsim in cloudsims:
        try:
            print("Launching from %s" % (cloudsim))
            cloudsim.launch_constellation(provider, configuration)
        except Exception, e:
            print("   Error: %s" % e)
        time.sleep(delay)

