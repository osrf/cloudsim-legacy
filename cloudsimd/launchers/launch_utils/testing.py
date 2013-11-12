from __future__ import with_statement
from __future__ import print_function


import os
import sys


def get_test_dir():
    p = os.path.abspath(__file__)
    d = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(p))))
    test_dir = os.path.join(d, 'test-reports')
    r = os.path.abspath(test_dir)
    return r


def get_test_path(fname):
    d = get_test_dir()
    p = os.path.join(d, fname)
    abs_path = os.path.abspath(p)
    return abs_path


def flush():
    pass


def get_test_runner():
    """
    Returns a test runner instance for unittest.main. This object captures
    the test output and saves it as an xml file. 
    """
    try:
        import xmlrunner
        path = get_test_dir()
        runner = xmlrunner.XMLTestRunner(output=path)
        return runner
    except Exception, e:
        print("get_test_runner error: %s" % e)
        return None


def kill_all_ec2_instances(ec2):
    #import boto
    #ec2 = boto.connect_ec2(aws_access_key_id="x", aws_secret_access_key="x")
    ec2.terminate_instances([reservation.instances[0].id for
                             reservation in ec2.get_all_instances()])


def get_softlayer_path():
    d = get_test_dir()
    r = os.path.abspath(d + '/../../softlayer.json')
    return r


def get_boto_path():
    d = get_test_dir()
    r = os.path.abspath(d + '/../../boto.ini')
    return r


if __name__ == "__main__":
    pass
