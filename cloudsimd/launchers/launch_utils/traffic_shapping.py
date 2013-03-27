import sshclient
from launch_db import get_constellation_data
import os
import redis
import logging

def log(msg, channel = "traffic_shapping"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
    except:
        print("Warning: redis not installed.")
    print("traffic_shapping log> %s" % msg)


def run_tc_command(constellation_name, machine_name_key, sshkey_key, ip_address_key, target_packet_latency, 
                   uplink_data_cap, downlink_data_cap):  

    constellation = get_constellation_data( constellation_name)
    keyDirectory = os.path.join(constellation['constellation_directory'])
    keyDirectory = os.path.join(keyDirectory, constellation[machine_name_key])
    keyPairName = constellation[sshkey_key]
    ip = constellation[ip_address_key]
    
    cmd = 'redis-cli set ts_targetLatency ' + str(target_packet_latency)
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)  
    log("ssh %s = %s" % (cmd, r) )