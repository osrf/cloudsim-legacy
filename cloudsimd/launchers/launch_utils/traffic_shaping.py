import sshclient
from launch_db import get_constellation_data
from launch_db import log_msg


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def run_tc_command(constellation_name, machine_name_key,
                   keyPairName,
                   ip_address_key,
                   target_latency,
                   uplink_cap, downlink_cap):

    constellation = get_constellation_data(constellation_name)
    keyDirectory = constellation['constellation_directory']
    ip = constellation[ip_address_key]

    cmd = 'redis-cli set vrc_target_outbound_latency %s' % target_latency
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)
    log("ssh %s = %s" % (cmd, r))

    # Note that we convert from bits (specified in the task description)
    # to bytes (used by the vrc network monitoring tools)
    limit = int(uplink_cap) / 8
    cmd = 'redis-cli set vrc/bytes/limit/uplink %s' % limit
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)

    limit = int(downlink_cap) / 8
    cmd = 'redis-cli set vrc/bytes/limit/downlink %s' % limit
    ssh = sshclient.SshClient(keyDirectory, keyPairName, 'ubuntu', ip)
    r = ssh.cmd(cmd)
    log("ssh %s = %s" % (cmd, r))
