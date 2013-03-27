import unittest
import os




class CloudCredentials(object):
    """
    Class that manages all the AWS credentials.
    """

    def __init__(self,
                 aws_access_key_id,
                 aws_secret_access_key,
                 ec2_region_name,
                 fname):
        """
        Constructor.
        @param aws_access_key_id: uniquely identifies user who owns account
        @type aws_access_key_id: string
        @param aws_secret_access_key: password
        @type aws_secret_access_key: string
        @param ec2_region_name: geographic area
        @type ec2_region_name: string
        @param ec2_region_endpoint: End point to direct the requests
        @type ec2_region_endpoint: string
        @param fname: boto config file name
        @type fname: string
        """
        
        ec2_region_endpoint='ec2.amazonaws.com',
        if ec2_region_name.startswith('eu-west'):
            ec2_region_endpoint = 'ec2.eu-west-1.amazonaws.com'
            
        self.fname = fname
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
        self.config_text = """
[Credentials]
aws_access_key_id = %s
aws_secret_access_key = %s

[Boto]
ec2_region_name = %s
ec2_region_endpoint = %s
""" % (aws_access_key_id, self.aws_secret_access_key,
       ec2_region_name, ec2_region_endpoint)

    def save(self):
        """
        Save the current credentials on a given file.
        """
        with open(self.fname, 'w') as f:
            f.write(self.config_text)

    def validate(self):
        """
        Check if the current credentials are valid.
        """
        from boto.ec2.connection import EC2Connection
        try:
            conn = EC2Connection(self.aws_access_key_id, self.aws_secret_access_key)
            conn.get_all_zones()
            return True
        except:
            pass
        return False


class Testotronics(unittest.TestCase):
    """
    Run unit tests of CloudCredentials
    """

#    def test_acredentials(self):
#        cloud = CloudCredentials('', '', 'us-east-1b',  fname='toto.cfg' )
#        valid = cloud.validate()
#        self.assert_(valid, "yo")

    def test_credentials(self):
        """
        Check if a wrong credential file is correctly not validated.
        Check if a wrong credential file is saved on disk after save()
        """
        cloud = CloudCredentials('key', 'secret', 'us-east-1d', fname='toto.cfg')
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
