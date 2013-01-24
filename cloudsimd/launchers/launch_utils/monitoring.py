from __future__ import print_function


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


def parse_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)