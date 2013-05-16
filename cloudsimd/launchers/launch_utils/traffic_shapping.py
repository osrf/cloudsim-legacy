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


def run_tc_command(constellation_name, machine_name_key, keyPairName, ip_address_key, target_packet_latency, 
                   uplink_data_cap, downlink_data_cap):  

    constellation = get_constellation_data(constellation_name)
    keyDirectory = constellation['constellation_directory']
    #keyDirectory = os.path.join(keyDirectory, constellation[machine_name_key])
    #keyPairName = constellation[sshkey_key]
    ip = constellation[ip_address_key]
    
    cmd = 'redis-cli set vrc_target_outbound_latency ' + str(target_packet_latency)
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)  
    log("ssh %s = %s" % (cmd, r) )
    
    # Note that we convert from bits (specified in the task description) to bytes (used by the vrc network monitoring tools)
    cmd = 'redis-cli set vrc/bytes/limit/uplink ' + str(int(uplink_data_cap)/8)
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)  
     
    cmd = 'redis-cli set vrc/bytes/limit/downlink ' + str(int(downlink_data_cap)/8)
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)  
    log("ssh %s = %s" % (cmd, r) )
