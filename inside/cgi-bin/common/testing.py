from __future__ import with_statement
from __future__ import print_function



import os
import boto

def get_test_dir():
    
    d = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    test_dir = os.path.join(d,'test-reports')
    r = os.path.abspath(test_dir)
    return r

def get_test_path(fname):
    d = get_test_dir()
    p = os.path.join(d,fname)
    abs_path = os.path.abspath(p)
    return abs_path

def get_test_runner():
    try:
        import xmlrunner
        path = get_test_dir()
        runner = xmlrunner.XMLTestRunner(output=path)
        return runner
    except:
        return None

def kill_all_ec2_instances(ec2):
    #import boto
    #ec2 = boto.connect_ec2(aws_access_key_id="foo", aws_secret_access_key="bar")
    ec2.terminate_instances([reservation.instances[0].id for reservation in ec2.get_all_instances()])
    

def get_boto_path():
    d = get_test_dir()
    r = os.path.abspath(d +'/../../boto.ini' )
    return r

if __name__ == "__main__":   
    print(get_test_dir())

    boto  = boto.pyami.config.Config(get_boto_path())
    ec2 = boto.connect_ec2()
    kill_all_ec2_instances(ec2)