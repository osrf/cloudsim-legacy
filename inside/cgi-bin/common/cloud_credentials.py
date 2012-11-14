import unittest
import os

from constants import BOTO_CONFIG_FILE_USEAST

class CloudCredentials(object):
    
    def __init__(self, 
                 aws_access_key_id, 
                 aws_secret_access_key, 
                 ec2_region_name = 'us-east-1', 
                 ec2_region_endpoint = 'ec2.amazonaws.com', 
                 fname = BOTO_CONFIG_FILE_USEAST ):
        
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
"""    % (aws_access_key_id, self.aws_secret_access_key, ec2_region_name, ec2_region_endpoint)
        
        
    
    def save(self ):
        with open(self.fname, 'w') as f:
            f.write(self.config_text)
            f.close()

    def validate(self):
        from boto.ec2.connection import EC2Connection
        try:
            conn = EC2Connection(self.aws_access_key_id, self.aws_secret_access_key)
            conn.get_all_zones()
        except:
            return False
        return True
        

class Testotronics(unittest.TestCase):

   
    def test_credentials(self):
        cloud = CloudCredentials('aws_access_key_id', 'aws_secret_access_key', 'ec2_region_name', 'ec2_region_endpoint', 'toto.cfg' )
        valid = cloud.validate()
        self.assert_(valid == False, "valid?")
        cloud.save()
        self.assert_(os.path.exists('toto.cfg'), 'no cred!')
         
        
if __name__ == '__main__':
    print('cloudy TESTS')
    unittest.main()    


