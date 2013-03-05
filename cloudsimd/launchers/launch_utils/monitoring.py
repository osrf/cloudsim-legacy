from __future__ import print_function
import time
import unittest

machine_states = [ 'terminated', 'terminating', 'stopped' 'stopping', 'nothing', 'starting', 'booting','network_setup', 'packages_setup', 'rebooting', 'running',  'simulation_running']
constellation_states = ['terminated', 'terminating','launching', 'running']

LATENCY_TIME_BUFFER = 40

def get_aws_states(ec2conn, machine_names_to_ids):
    

    aws_states = {}
    
    ids_to_machine_names = dict((v,k) for k,v in machine_names_to_ids.iteritems())
    
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for instance in instances:
        aws_is = instance.id
        if aws_is in ids_to_machine_names:
            state = instance.state
            machine = ids_to_machine_names[aws_is]
            aws_states[machine] = state
            
    return aws_states


def _parse_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)


def _accumulate_ping_data(data, mini, avg, maxi, mdev, cutoff_time_span = 40):
    time_now = time.time()
    data.insert(0, [time_now, mini, avg, maxi, mdev])
    
    done = False
    while not done:
        time_of_oldest_sample = data[-1][0]
        time_span = time_now - time_of_oldest_sample
        if time_span < cutoff_time_span:
            done = True
        else:
            data.pop() # forget last sample


def record_ping_result(data_str, ping_str, cutoff_time_span):
    """
    Takes a ping result, parses it and keeps in a time stamped list.
    Old samples are discarded
    """
    data = eval(data_str)
    mini, avg, maxi, mdev  = _parse_ping_data(ping_str)
    _accumulate_ping_data(data, mini, avg, maxi, mdev, cutoff_time_span)
    s = "%s" % data
    return s

class Testos(unittest.TestCase):
    def test_me(self):
        data = []
        for i in range(10):
            _accumulate_ping_data(data, mini=i, avg=i, maxi=i, mdev=i, cutoff_time_span = 0.4)
            time.sleep(0.1)
            print(data)
        
if __name__ == "__main__":
    print("test")
    unittest.main()
    
    