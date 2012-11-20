from __future__ import with_statement
from __future__ import print_function



import os

def get_test_dir():
    d = os.path.split(__file__)[0]
    test_dir = os.path.join('..','..','..', 'test-reports')
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
    
if __name__ == "__main__":   
    print(get_test_dir())
    