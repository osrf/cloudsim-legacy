from __future__ import print_function
import time
import unittest
from launch_db import ConstellationState
from launch import aws_connect
import redis
import logging
from sshclient import SshClient
import commands

machine_states = [ 'terminated', 'terminating', 'stopped' 'stopping', 'nothing', 'starting', 'booting','network_setup', 'packages_setup', 'rebooting', 'running',  'simulation_running']
constellation_states = ['terminated', 'terminating','launching', 'running']

LATENCY_TIME_BUFFER = 60

def log(msg, channel = "monitor"):
    try:
        
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("monitoring log> %s" % msg)

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


def parse_dpkg_line(s):
    """
    takes a line from /var/log/dpkg.log 
    removes the date part of the file for readability
    """
    r = s.split("status ")[1]
    if len(r) ==  0:
        return s
    return r.strip()


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

def update_machine_aws_states(credentials_ec2, constellation_name, aws_id_keys_to_state_keys_dict):
    """
    Updates the redis database with aws state of machines for a constellation.
    The dictionnary contains the keys to the aws ids and mapped to the keys of the states
    
    in the case of {'router_aws_id':'router_aws_state'}, the aws id is read from the 'router_aws_id' value and
    written to the 'router_aws_state' value
    
    Some keys may not exist (too early in the launch process)
    """
    constellation = ConstellationState(constellation_name)
    aws_ids = {}
    for aws_id_key in aws_id_keys_to_state_keys_dict.keys():
        try:
            aws_id = constellation.get_value(aws_id_key)
            if aws_id != None: 
                aws_ids[aws_id_key] = aws_id
        except:
            pass # machine is not up yet
        
    if len(aws_ids):   
        ec2conn = aws_connect(credentials_ec2)[0] 
        aws_states = get_aws_states(ec2conn, aws_ids)
        for aws_id_key, aws_state in  aws_states.iteritems():
            state_key = aws_id_keys_to_state_keys_dict[aws_id_key]
            constellation.set_value(state_key, aws_state)


    
def constellation_is_terminated(constellation_name):
    try:
        constellation = ConstellationState(constellation_name)
        constellation_state = constellation.get_value("constellation_state") 
        # log("constellation %s state %s" % (constellation_name, constellation_state) )
        if constellation_state == "terminated":
            # constellation.expire(30)
            log("Constellation  %s is terminated" % constellation_name)
            return True
    except:
        log("Can't access constellation  %s data" % constellation_name)
        # constellation.expire(30)
        return True

def get_ssh_client(constellation_name, machine_state, ip_key, sshkey_key):
    """
    Checks to see if machine is ready and creates an ssh client accordingly
    """
    ssh_client = None
    constellation = ConstellationState(constellation_name)
    if machine_states.index(machine_state) >= machine_states.index('packages_setup'):
        constellation_directory = constellation.get_value('constellation_directory')
        machine_ip = constellation.get_value(ip_key)
        key_pair_name = constellation.get_value(sshkey_key)
        ssh_client = SshClient(constellation_directory, key_pair_name, 'ubuntu', machine_ip)
    return ssh_client


def monitor_launch_state(constellation_name, ssh_client,  machine_state, dpkg_cmd, launch_msg_key):
    
    if ssh_client == None: # too early to verify 
        return 
    
    #log("monitor_launch_state %s/%s %s" % (constellation_name, launch_msg_key, machine_state) )
    constellation = ConstellationState(constellation_name)
    constellation_state = constellation.get_value("constellation_state")
    #log("const state %s" % constellation_state)
    
    if constellation_states.index(constellation_state ) >= constellation_states.index("launching"):
        if machine_state == "running":
            constellation.set_value(launch_msg_key, "complete")       
            log("complete")
            
        if machine_state == 'packages_setup':
            try:
                dpkg_line = ssh_client.cmd(dpkg_cmd)# "bash cloudsim/dpkg_log_robot.bash"
                robot_package = parse_dpkg_line(dpkg_line)
                current_value = constellation.get_value(launch_msg_key)
                log("xx %s" % robot_package)
                if current_value != robot_package:
                    constellation.set_value(launch_msg_key, robot_package)
                    log('%s/%s = %s' % (constellation_name, dpkg_cmd, robot_package) )
            except Exception, e:
                log("%s error: %s" % (dpkg_cmd, e))            

def monitor_simulator(constellation_name, ssh_client):
    """
    Detects if the simulator is running and writes the 
    result into the "gazebo" ditionnary key 
    """
    if ssh_client == None:
        #constellation.set_value("gazebo", "not running")
        return False
    
    constellation = ConstellationState(constellation_name)
    simulation_state = constellation.get_value('simulation_state')
    if machine_states.index(simulation_state) >= machine_states.index('running'):
        gl_state = constellation.get_value("simulation_glx_state")
        if gl_state == "running":
            try:
                ping_gazebo = ssh_client.cmd("bash cloudsim/ping_gazebo.bash")
                log("cloudsim/ping_gazebo.bash = %s" % ping_gazebo )
                constellation.set_value("gazebo", "running")
            except Exception, e:
                log("monitor: cloudsim/ping_gazebo.bash error: %s" % e )
                constellation.set_value("gazebo", "not running")
                return False      
    return True

def _monitor_ping(constellation_name, ping_data_key, ping_str):
    """
    internal implementation for monitor_cloudsim_ping and monitor_ssh_ping
    """
    constellation = ConstellationState(constellation_name)
    latency = constellation.get_value(ping_data_key)
    latency = record_ping_result(latency, ping_str, LATENCY_TIME_BUFFER)
    constellation.set_value(ping_data_key, latency)
    

def monitor_cloudsim_ping(constellation_name, ip_address_key, ping_data_key):
    """
    Finds the ip of the machine to pind in redis, pings the machine and integrates
    the results with the existing data.
    The ping is done from CloudSim
    """
    constellation = ConstellationState(constellation_name)
    ip_address = constellation.get_value(ip_address_key)
    o, ping_str = commands.getstatusoutput("ping -c3 %s" % ip_address)
    if o == 0:
        _monitor_ping(constellation_name, ping_data_key, ping_str) 
        
def monitor_ssh_ping(constellation_name, ssh_client, ip_address, ping_data_key):
    """
    Pings a machine and integrates the results with the existing data into the 
    database. The ping is done from the ssh client (i.e router computer)
    """
    if ssh_client == None:
        return 
    ping_str = ssh_client.cmd("ping -c3 %s" % ip_address)
    _monitor_ping(constellation_name, ping_data_key, ping_str)
    
    

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
    
    