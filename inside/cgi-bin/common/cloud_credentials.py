import unittest
import os
import json
from common.constants import update_cloudsim_configuration_list
import SoftLayer.API


class SoftLayerCredentials(object):
    """
    Class that manages the SoftLayer credentials.
    """

    def __init__(self,
                 name,
                 api_key,
                 fname):
        self.fname = fname
        self.osrf_creds = {'user': name, 'api_key': api_key}

    def save(self):
        with open(self.fname, 'w') as f:
            s = json.dumps(self.osrf_creds)
            f.write(s)
        update_cloudsim_configuration_list()

    def validate(self):
        api_username = self.osrf_creds['user']
        api_key = self.osrf_creds['api_key']

        domain_id = None
        client = SoftLayer.API.Client('SoftLayer_Account',
                                      domain_id, api_username, api_key)
        valid = True
        try:
            x = client['Account'].getObject()
            print("valid SoftLayerCredentials %s" % x)
        except Exception, e:
            valid = False
            print("not valid: %s" % e)
        return valid


class CloudCredentials(object):
    """
    Class that manages all the AWS credentials.
    """

    def __init__(self,
                 aws_access_key_id,
                 aws_secret_access_key,
                 us_east1_az,
                 eu_west_az,
                 us_west2_az,
                 fname):
        """
        Constructor.
        @param aws_access_key_id: uniquely identifies user who owns account
        @param aws_secret_access_key: password
        @param fname: boto config file name of file
        """
        self.us_east1_az = us_east1_az
        self.eu_west_az = eu_west_az
        self.us_west2_az = us_west2_az

        self.fname = fname
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key

    def save(self, ec2_region_name="us-east-1"):
        """
        Save the current credentials on a given file.
        """
        endpoints = {"us-east-1": "ec2.us-east-1.amazonaws.com",
                    "us-west-2": "ec2.us-west-2.amazonaws.com",
                    "us-west-1": "ec2.us-west-1.amazonaws.com",
                    "eu-west-1": "ec2.eu-west-1.amazonaws.com",
                    "ap-southeast-1": "ec2.ap-southeast-1.amazonaws.com",
                    "ap-southeast-2": "ec2.ap-southeast-2.amazonaws.com",
                    "ap-northeast-1": "ec2.ap-northeast-1.amazonaws.com",
                    "sa-east-1": "ec2.sa-east-1.amazonaws.com"}

        ec2_region_endpoint = endpoints[ec2_region_name]
        config_text = """
[Credentials]
aws_access_key_id = %s
aws_secret_access_key = %s

[Boto]
ec2_region_name = %s
ec2_region_endpoint = %s

[CloudSim]
us-east-1 = %s
us-west-2 = %s
eu-west-1 = %s

""" % (self.aws_access_key_id, self.aws_secret_access_key,
       ec2_region_name, ec2_region_endpoint, self.us_east1_az,
       self.eu_west_az,
       self.us_west2_az)

        with open(self.fname, 'w') as f:
            f.write(config_text)

    def validate(self):
        """
        Check if the current credentials are valid.
        """
        from boto.ec2.connection import EC2Connection
        try:
            conn = EC2Connection(self.aws_access_key_id,
                                 self.aws_secret_access_key)
            conn.get_all_zones()
            return True
        except:
            pass
        return False


class Testotronics(unittest.TestCase):
    """
    Run unit tests of CloudCredentials
    """

    def test_credentials(self):
        """
        Check if a wrong credential file is correctly not validated.
        Check if a wrong credential file is saved on disk after save()
        """
        cloud = CloudCredentials('key', 'secret', 'us-east-1d',
                                 fname='toto.cfg')
        valid = cloud.validate()
        self.assert_(not valid, "error: 'key' is not a valid key")
        cloud.save()
        self.assert_(os.path.exists('toto.cfg'), 'no cred!')

    def tearDown(self):
        """
        Remove the credential files created after each test
        """
        if os.path.exists('toto.cfg'):
            os.remove('toto.cfg')


if __name__ == '__main__':
    print('cloudy TESTS')
    unittest.main()
