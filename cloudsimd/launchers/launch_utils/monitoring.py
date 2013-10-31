from __future__ import print_function
import time
import unittest
from launch_db import ConstellationState
from sshclient import SshClient
import commands
import traceback
from launch_db import log_msg
import redis
import json
from aws import aws_connect

machine_states = ['terminated', 'terminating', 'stopped' 'stopping',
                  'nothing', 'starting', 'booting',
                  'network_setup', 'packages_setup', 'rebooting',
                  'running',  'simulation_running']
constellation_states = ['terminated', 'terminating', 'launching', 'running']
LATENCY_TIME_BUFFER = 60


def log(msg, channel=__name__, severity="debug"):
    log_msg(msg, channel, severity)


def get_aws_states(ec2conn, machine_names_to_ids):
    aws_states = {}
    ids_to_machine_names = dict((v, k)
                                for k, v in machine_names_to_ids.iteritems())

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
    if len(r) == 0:
        return s
    return r.strip()


def _parse_ping_data(ping_str):
    values = [float(x) for x in ping_str.split()[-2].split('/')]
    if len(values) == 5:
        values = values[1:]
    mini, avg, maxi, mdev = values
    return (mini, avg, maxi, mdev)


def _accumulate_ping_data(data, mini, avg, maxi, mdev, cutoff_time_span=40):
    time_now = time.time()
    data.insert(0, [time_now, mini, avg, maxi, mdev])

    done = False
    while not done:
        time_of_oldest_sample = data[-1][0]
        time_span = time_now - time_of_oldest_sample
        if time_span < cutoff_time_span:
            done = True
        else:
            data.pop()  # forget last sample


def record_ping_result(data_str, ping_str, cutoff_time_span):
    """
    Takes a ping result, parses it and keeps in a time stamped list.
    Old samples are discarded
    """
    data = None
    try:
        data = eval(data_str)
    except:
        pass
    mini, avg, maxi, mdev = (0.0, 0.0, 0.0, 0.0)
    try:
        mini, avg, maxi, mdev = _parse_ping_data(ping_str)
    except:
        pass
    _accumulate_ping_data(data, mini, avg, maxi, mdev, cutoff_time_span)
    s = "%s" % data
    return s


def constellation_is_terminated(constellation_name):
    constellation = None
    expire = True
    try:
        constellation = ConstellationState(constellation_name)
        constellation_state = constellation.get_value("constellation_state")
        expire = constellation_state == "terminated"
    except:
        log("Can't access constellation  %s data" % constellation_name)

    if expire:
        try:
            constellation.expire(1)
        except:
            pass
    return expire


def get_ssh_client(constellation_name, machine_state, ip_key, sshkey_key):
    """
    Checks to see if machine is ready and creates an ssh client accordingly
    """
    ssh_client = None
    constellation = ConstellationState(constellation_name)
    if machine_states.index(machine_state) >= machine_states.index(
                                                            'packages_setup'):
        constellation_directory = constellation.get_value(
                                                'constellation_directory')
        machine_ip = constellation.get_value(ip_key)
        key_pair_name = constellation.get_value(sshkey_key)
        ssh_client = SshClient(constellation_directory,
                               key_pair_name,
                               'ubuntu',
                               machine_ip)
    return ssh_client


def monitor_launch_state(constellation_name, ssh_client,
                         machine_state,
                         dpkg_cmd,
                         launch_msg_key):

    if ssh_client == None:  # too early to verify
        return
    try:
        constellation = ConstellationState(constellation_name)
        constellation_state = constellation.get_value("constellation_state")
        if constellation_states.index(constellation_state) >= \
                                constellation_states.index("launching"):
            #if machine_state == "running":
            #    constellation.set_value(launch_msg_key, "complete")
            if machine_state == 'packages_setup':
                dpkg_line = ssh_client.cmd(dpkg_cmd)
                package_msg = parse_dpkg_line(dpkg_line)
                current_value = constellation.get_value(launch_msg_key)
                if current_value != package_msg:
                    constellation.set_value(launch_msg_key, package_msg)
    except:
        tb = traceback.format_exc()
        log("monitor_launch_state traceback:  %s" % tb)


def monitor_simulator(constellation_name,
                      ssh_client,
                      sim_state_key='sim_state'):
    """
    Detects if the simulator is running and writes the
    result into the "gazebo" dictionary key
    """
    if ssh_client == None:
        #constellation.set_value("gazebo", "not running")
        return False

    constellation = ConstellationState(constellation_name)
    simulation_state = constellation.get_value(sim_state_key)
    if machine_states.index(simulation_state) >= \
                            machine_states.index('running'):
        gl_state = constellation.get_value("sim_glx_state")
        if gl_state == "running":
            try:
                out = ssh_client.cmd("bash cloudsim/ping_gazebo.bash")
                #log("ping_gazebo returned [%s]" % out)
                if out == "":
                    constellation.set_value("gazebo", "not running")
                    return False
            except Exception, e:
                log("monitor: cloudsim/ping_gazebo.bash error: %s" % e)
                constellation.set_value("gazebo", "not running")
                return False
    constellation.set_value("gazebo", "running")
    return True


def monitor_gzweb(constellation_name, ssh_client, sim_state):
    """
    Detects if the gzweb is running and writes the
    url into the "gzweb" dictionary key
    """
    gzweb_key = "gzweb"
    constellation = ConstellationState(constellation_name)
    simulation_state = constellation.get_value('sim_state')
    if machine_states.index(simulation_state) >= \
                            machine_states.index('running'):
        gl_state = constellation.get_value("gazebo")
        if gl_state == "running":
            try:
                # current_state = constellation.get_value(gzweb_key)
                out = ssh_client.cmd("bash cloudsim/ping_gzweb.bash")
                log("ping_gzweb returned [%s]" % out)
                if out == "":
                    constellation.set_value(gzweb_key, "not running")
                    return False
                else:
                    constellation.set_value(gzweb_key, "running")
                    return True
            except Exception, e:
                log("monitor: cloudsim/ping_gzweb.bash error: %s" % e)
                constellation.set_value(gzweb_key, "")
                return False
    return False


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
    Finds the ip of the machine to pind in redis,
    pings the machine and integrates
    the results with the existing data.
    The ping is done from CloudSim
    """
    constellation = ConstellationState(constellation_name)
    if constellation.has_value(ip_address_key):
        ip_address = constellation.get_value(ip_address_key)
        o, ping_str = commands.getstatusoutput("ping -c3 %s" % ip_address)
        if o == 0:
            _monitor_ping(constellation_name, ping_data_key, ping_str)


def monitor_ssh_ping(constellation_name,
                     ssh_client,
                     ip_address,
                     ping_data_key):
    """
    Pings a machine and integrates the results with the existing data into the
    database. The ping is done from the ssh client (i.e router computer)
    """
    if ssh_client == None:
        return
    try:
        ping_str = ssh_client.cmd("ping -c3 %s" % ip_address)
        _monitor_ping(constellation_name, ping_data_key, ping_str)
    except:
        tb = traceback.format_exc()
        log("monitor_ssh_ping traceback:  %s" % tb)
        constellation = ConstellationState(constellation_name)
        constellation.set_value(ping_data_key, "[]")


class TaskTimeOut(Exception):
    def __init__(self, message, task):
        Exception.__init__(self, message)
        self.task = task


def monitor_task(constellation_name, ssh_router):
    """
    Read score and net usage data.
    Aborts tasks that timeout
    """
    def parse_score_data(score_str):
        toks = score_str.split()
        keys = [x[6:] for x in toks[-2].split(',')]
        keys[0] = 'time'
        # keys = ['time', 'wall_time', 'sim_time', 'wall_time_elapsed',
        # 'sim_time_elapsed', 'completion_score',
        # 'falls', 'message',  'task_type']
        values_str = toks[-1]
        values = values_str.split(',')
        d = dict(zip(keys, values))
        score = d['completion_score']
        sim_time = float(d['sim_time']) / 1e9
        fall_count = d['falls']
        msg = d['message']
        return (score, sim_time, fall_count, msg)

    #log("monitor_task BEGIN")
    constellation = ConstellationState(constellation_name)
    task_id = constellation.get_value("current_task")

    if task_id != "":
        sim_time = 0
        timeout = 0

        task = constellation.get_task(task_id)
        timeout = int(task['timeout'])
        score_str = None
        try:
            s = ssh_router.cmd("cloudsim/get_score.bash")
            log(s)
            score, sim_time, fall_count, msg = parse_score_data(s)
            score_str = ""
            #score_str += "<b>%s</b>: %s. " % ("score", score)
            score_str += "<b>%s</b>: %s. " % ("sim time",   sim_time)
            score_str += " %s" % (msg)
            score_str += "<b>falls:</b> %s." % fall_count

        except Exception, e:
            #score_str = "No score available."
            tb = traceback.format_exc()
            log("traceback: %s" % tb)
        log("score %s" % score_str)
        net_str = None

        try:
            n = ssh_router.cmd("cloudsim/get_network_usage.bash")
            log(n)
            toks = n.split()
            up_bits = int(toks[2]) * 8
            down_bits = int(toks[3]) * 8
            up_cap = int(task['uplink_data_cap'])
            down_cap = int(task['downlink_data_cap'])

            up = 0.0
            down = 0.0
            if up_cap != 0.0:
                up = 100.0 * up_bits / up_cap
            if down_cap != 0.0:
                down = 100.0 * down_bits / down_cap
            net_str = "<b>up/down link (%%)</b>: %0.2f / %0.2f" % (up, down)
        except Exception, e:
            # net_str = "no network usage available"
            log("score monitoring error %s" % e)
            tb = traceback.format_exc()
            log("traceback:  %s" % tb)

        net_str = None
        final_score = ""
        if net_str:
            final_score += "%s " % net_str
        if score_str:
            final_score += "%s" % score_str
        log("score %s" % final_score)
        constellation.update_task_value(task['task_id'],
                                            'task_message',
                                            final_score)
        if sim_time > timeout:
            task = constellation.get_task(task_id)
            timeout_msg = ' [Timeout]'
            msg = task['task_message']
            if  msg.find(timeout_msg) < 0:
                msg += timeout_msg
                constellation.update_task_value(task['task_id'],
                                                'task_message',
                                                msg)

            task = constellation.get_task(task_id)
            if task['task_state'] == 'running':
                log("TASKTIMEOUT")
                d = {}
                d['command'] = 'stop_task'
                d['constellation'] = constellation_name
                #stop_task(constellation_name, task)
                r = redis.Redis()
                s = json.dumps(d)
                r.publish("cloudsim_cmds", s)
    #log("monitor_task END")


class Testos(unittest.TestCase):
    def test_me(self):
        data = []
        for i in range(10):
            _accumulate_ping_data(data,
                                  mini=i,
                                  avg=i,
                                  maxi=i,
                                  mdev=i,
                                  cutoff_time_span=0.4)
            time.sleep(0.1)
            print(data)


if __name__ == "__main__":
    print("test")
    unittest.main()
