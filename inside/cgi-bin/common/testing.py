from __future__ import with_statement
from __future__ import print_function


import xmlrunner
import os

def get_test_dir():
    d = os.path.split(__file__)[0]
    test_dir = os.path.join('..','..','..', 'test-reports')
    r = os.path.abspath(test_dir)
    return r


def get_test_runner():
    path = get_test_dir()
    runner = xmlrunner.XMLTestRunner(output=path)
    return runner
    
if __name__ == "__main__":   
    print(get_test_dir())
    