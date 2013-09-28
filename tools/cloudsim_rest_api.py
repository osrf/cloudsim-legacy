import requests
import urllib2

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

    def get_constellations(self):
        r = self._api_get('cloudsim/inside/cgi-bin/constellations')
        return r

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

    def update_constellation(constellation_name):
        url = '/cloudsim/inside/cgi-bin/constellations';
        url += '/' + constellation_name;
        s = self._api_put(url)
        return s
    
