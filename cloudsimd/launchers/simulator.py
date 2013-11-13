from __future__ import print_function

import unittest
import os
import time
import zipfile
import shutil
import json
import subprocess
import dateutil.parser
import multiprocessing
import sys

from launch_utils.traffic_shaping import  run_tc_command


from launch_utils.monitoring import constellation_is_terminated,\
    monitor_launch_state,  monitor_ssh_ping,\
    monitor_task, monitor_simulator, TaskTimeOut, monitor_gzweb

from launch_utils.softlayer import create_openvpn_key

from launch_utils.launch_db import get_constellation_data, ConstellationState,\
    get_cloudsim_config, log_msg

from launch_utils.startup_scripts import create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file,\
    create_ssh_connect_file, get_simulator_script,\
    get_simulator_deploy_script

from launch_utils.sshclient import SshClient
from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue

from launch_utils.aws import acquire_aws_single_server, terminate_aws_server,\
    get_aws_ubuntu_sources_repo

from launch_utils import LaunchException


OPENVPN_SERVER_IP = '11.8.0.1'
OPENVPN_CLIENT_IP = '11.8.0.2'
SIM_IP = '10.0.0.50'

launch_sequence = ["nothing", "os_reload", "launch", "init_router",
                   "init_privates", "zip", "change_ip", "startup",
                   "block_public_ips", "reboot", "running"]


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def start_gzweb(constellation_name):
    log("start_gzweb for %s" % (constellation_name))
    ssh_client = _get_ssh_client(constellation_name)
    o = ssh_client.cmd("cloudsim/start_gzweb.bash")
    log("GZWEB started for %s: %s" % (constellation_name, o))


def stop_gzweb(constellation_name):
    log("stop_gzweb for %s" % (constellation_name))
    ssh_client = _get_ssh_client(constellation_name)
    o = ssh_client.cmd("cloudsim/stop_gzweb.bash")
    log("GZWEB stopped for %s: %s" % (constellation_name, o))


def update(constellation_name):
    """
    Update the constellation software on the servers.
    This function is a plugin function that should be implemented by
    each constellation type
    """
    constellation = ConstellationState(constellation_name)
    ssh_client = _get_ssh_client(constellation_name)
    machines = constellation.get_value('machines')
    for machine in machines:
        constellation.set_value("%s_state" % machine, "packages_setup")
        constellation.set_value("%s_launch_msg" % machine, "updating software")
    try:
        o = ssh_client.cmd("cloudsim/update_constellation.bash")
        log("UPDATE: %s" % o, "toto")
    finally:
        for machine in machines:
            constellation.set_value("%s_state" % machine, "running")
            constellation.set_value("%s_launch_msg" % machine, "complete")
        log("UPDATE DONE", "toto")


def get_ping_data(ping_str):
    mini, avg, maxi, mdev = [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)


def _start_simulator(constellation_name,
                    package_name,
                    launch_file_name,
                    launch_args,
                    task_timeout):
    ssh_client = _get_ssh_client(constellation_name)
    c = "bash cloudsim/start_sim.bash %s %s %s" % (package_name,
                                                   launch_file_name,
                                                   launch_args)
    cmd = c.strip()
    r = ssh_client.cmd(cmd)
    log('_start_simulator %s' % r)


def _stop_simulator(constellation_name):
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_client = _get_ssh_client(constellation_name)
    r = ssh_client.cmd(cmd)
    log('_stop_simulator %s' % r)


def start_task(constellation_name, task):

    log("START TASK %s for %s" % (constellation_name, task))

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation_name,
                   'sim_machine_name',
                   'key-sim',
                   'sim_public_ip',
                   latency, up, down)

    log("** START SIMULATOR ***")
    try:
        _start_simulator(constellation_name,
                    task['ros_package'],
                    task['ros_launch'],
                    task['ros_args'],
                    task['timeout'])
    finally:
        log("START TASK  DONE %s for %s" % (constellation_name, task))


def stop_task(constellation, task):

    log("** CONSTELLATION %s *** STOP TASK %s ***" % (constellation,
                                                      task['task_id']))
    _stop_simulator(constellation)

    log("** Notify portal ***")
    notify_portal(constellation, task)


def check_for_end_of_task(constellation_name, ssh_client):
    if monitor_task(constellation_name, ssh_client):
        raise TaskTimeOut()


def _get_ssh_client(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    sim_ip = constellation.get_value("sim_public_ip")
    ssh_client = SshClient(constellation_directory,
                           "key-sim",
                           'ubuntu',
                           sim_ip)
    return ssh_client


def ssh_ping_proc(constellation_name, ip, latency_key, counter):
    ssh_client = _get_ssh_client(constellation_name)
    monitor_ssh_ping(constellation_name, ssh_client, ip, latency_key)
    log("ssh ping_proc() ENDS %s %s" % (latency_key, counter))


def monitor_task_proc(constellation_name, counter):
    ssh_client = _get_ssh_client(constellation_name)
    monitor_task(constellation_name, ssh_client)
    log("monitor_task_proc() ENDS %s" % counter)


def monitor_simulator_proc(constellation_name, counter):
    ssh_client = _get_ssh_client(constellation_name)
    monitor_simulator(constellation_name, ssh_client, "sim_state")
    log("monitor_simulator_proc() ENDS %s" % counter)


def monitor_gzweb_proc(constellation_name, counter):
    ssh_client = _get_ssh_client(constellation_name)
    monitor_gzweb(constellation_name, ssh_client, "sim_state")
    log("monitor_gzweb_proc() ENDS %s" % counter)


def monitor_launch(constellation_name, machine_name, counter):
    ssh_client = _get_ssh_client(constellation_name)
    constellation = ConstellationState(constellation_name)
    machine_state = constellation.get_value('%s_state' % machine_name)
    monitor_launch_state(constellation_name, ssh_client, machine_state,
                             "cloudsim/dpkg_log_%s.bash" % machine_name,
                             '%s_launch_msg' % machine_name)
    log("monitor_launch() ENDS %s %s" % (machine_name, counter))


def monitor(constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        log("monitor done for %s" % (constellation_name))
        return True  # stop the monitoring loop

    procs = []
    p = multiprocessing.Process(target=monitor_simulator_proc,
                            args=(constellation_name, counter))
    procs.append(p)

    p = multiprocessing.Process(target=monitor_task_proc,
                                    args=(constellation_name, counter))
    procs.append(p)

    p = multiprocessing.Process(target=monitor_gzweb_proc,
                            args=(constellation_name, counter))
    procs.append(p)

    p = multiprocessing.Process(target=ssh_ping_proc,
                    args=(constellation_name, OPENVPN_CLIENT_IP,
                          'sim_latency', counter))
    procs.append(p)

    for p in procs:
        p.start()

    monitor_launch(constellation_name, 'sim', counter)

    for p in procs:
        p.join()

    return False


def _init_computer_data(constellation_name, machines):

    constellation = ConstellationState(constellation_name)

    # init the redis db info
    constellation.set_value("gazebo", "not running")
    constellation.set_value("sim_glx_state", "not running")
    constellation.set_value("constellation_state", "launching")
    constellation.set_value("error", "")
    constellation.set_value("gazebo", "not running")
    constellation.set_value("gzweb", "")

    for prefix in machines:
        machine = machines[prefix]
        ip = machine['ip']
        constellation.set_value("%s_ip" % prefix, ip)
        constellation.set_value('%s_ip_address' % prefix, "nothing")
        constellation.set_value('%s_state' % prefix, "nothing")
        constellation.set_value('%s_aws_state' % prefix, 'pending')
        constellation.set_value('%s_launch_msg' % prefix, 'starting')
        constellation.set_value('%s_zip_file' % prefix, 'not ready')
        constellation.set_value('%s_latency' % prefix, '[]')
        constellation.set_value('%s_machine_name' % prefix,
                                '%s_%s' % (prefix, constellation_name))
        constellation.set_value('%s_key_name' % prefix, None)


def create_zip_file(zip_file_path, short_name, files_to_zip):

    with zipfile.ZipFile(zip_file_path, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(short_name, short_fname)
            fzip.write(fname, zip_name)


def create_private_machine_zip(machine_name_prefix,
                               machine_ip,
                               constellation_name,
                               constellation_directory,
                               key_prefix):

    machine_dir = os.path.join(constellation_directory, machine_name_prefix)
    os.makedirs(machine_dir)
    key_short_filename = '%s.pem' % key_prefix
    key_fpath = os.path.join(machine_dir, key_short_filename)
    shutil.copyfile(os.path.join(constellation_directory, key_short_filename),
             key_fpath)
    os.chmod(key_fpath, 0600)

    fname_ssh_sh = os.path.join(machine_dir,
                                'ssh-%s.bash' % machine_name_prefix)

    file_content = create_ssh_connect_file(key_short_filename, machine_ip)
    with open(fname_ssh_sh, 'w') as f:
        f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    vpn_key_short_filename = 'openvpn.key'
    vpnkey_fname = os.path.join(machine_dir, vpn_key_short_filename)
    shutil.copyfile(os.path.join(constellation_directory,
                                 vpn_key_short_filename),
             vpnkey_fname)
    os.chmod(vpnkey_fname, 0600)

    # create open vpn config file
    file_content = create_openvpn_client_cfg_file(machine_ip,
                    client_ip=OPENVPN_CLIENT_IP, server_ip=OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)

    fname_start_vpn = os.path.join(machine_dir, "start_vpn.bash")
    file_content = create_vpc_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755)

    fname_ros = os.path.join(machine_dir, "ros.bash")
    file_content = create_ros_connect_file(machine_ip=OPENVPN_CLIENT_IP,
                                           master_ip=SIM_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)

    files_to_zip = [key_fpath,
                    fname_ssh_sh,
                    vpnkey_fname,
                    fname_vpn_cfg,
                    fname_start_vpn,
                    fname_ros]

    fname_zip = os.path.join(machine_dir, "%s_%s.zip" % (machine_name_prefix,
                                                         constellation_name))
    create_zip_file(fname_zip, "%s_%s" % (machine_name_prefix,
                                          constellation_name), files_to_zip)
    return fname_zip


def _create_deploy_zip_files(constellation_name,
                     constellation_directory,
                     machines,
                     zipped_files=[]):

    deploy_script = get_simulator_deploy_script()

    # constellation = ConstellationState(constellation_name)
    deploy_dir = os.path.join(constellation_directory, "deploy")
    os.makedirs(deploy_dir)

    deploy_script_fname = os.path.join(deploy_dir, "deploy.bash")
    with open(deploy_script_fname, 'w') as f:
        f.write(deploy_script)

    files_to_zip = [fi for fi in zipped_files]
    files_to_zip.append(deploy_script_fname)
    for machine_name in machines:
        short_fname = "key-%s.pem" % machine_name
        fname_key = os.path.join(deploy_dir, short_fname)
        shutil.copy(os.path.join(constellation_directory, short_fname),
                    fname_key)
        os.chmod(fname_key, 0600)
        files_to_zip.append(fname_key)

    deploy_fname_zip = os.path.join(constellation_directory, "deploy.zip")
    create_zip_file(deploy_fname_zip, "deploy", files_to_zip)
    return deploy_fname_zip


def _create_zip_files(constellation_name,
                     constellation_directory,
                     machines):
    """
    Creates zip files for each machines. Different files are generated for
    user roles (ex: user_router.zip has no router ssh key)
    """
    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('zip'):
        return

    for machine_name, _ in machines.iteritems():
        machine_key_prefix = 'key-%s' % (machine_name)
        msg_key = '%s_launch_msg' % machine_name
        zip_ready_key = "%s_zip_file" % machine_name
        zip_fname = os.path.join(constellation_directory,
                                 "%s.zip" % machine_name)
        zip_user_fname = os.path.join(constellation_directory,
                                 "user_%s.zip" % machine_name)

        constellation.set_value(msg_key, 'creating zip file')
        if machine_name == "router":
            '''router_ip = constellation.get_value("router_public_ip")
            router_zip_fname, router_zip_user_fname = create_router_zip(
                                                    router_ip,
                                                    constellation_name,
                                                    machine_key_prefix,
                                                    constellation_directory)
            shutil.copy(router_zip_fname, zip_fname)
            shutil.copy(router_zip_user_fname, zip_user_fname)'''
            pass
        else:
            constellation.set_value(msg_key, 'creating zip files')
            ip = constellation.get_value('sim_public_ip')
            machine_zip_fname = create_private_machine_zip(machine_name,
                                               ip,
                                               constellation_name,
                                               constellation_directory,
                                               machine_key_prefix)
            shutil.copy(machine_zip_fname, zip_fname)
            if machine_name != "sim":
                shutil.copy(machine_zip_fname, zip_user_fname)
            else:
                zip_fname = os.path.join(constellation_directory,
                    "simulator.zip")
                shutil.copy(machine_zip_fname, zip_fname)
        constellation.set_value(zip_ready_key, 'ready')

    constellation.set_value("launch_stage", "zip")


def _reboot_machines(constellation_name,
                     ssh_client,
                    machine_names,
                    constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('reboot'):
        return

    #constellation.set_value('router_aws_state', m)
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       "cloudsim/setup/done",
                       "running")
    constellation.set_value('router_launch_msg',
                                    "Waiting for constellation reboot")
    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name,
                                    "Rebooting after software installation")
        constellation.set_value('%s_aws_state' % machine_name, "rebooting")

    for machine_name in machine_names:
        ssh_client.cmd("cloudsim/reboot_%s.bash" % machine_name)
    log("waiting before connecting after reboot")
    time.sleep(20)
    constellation.set_value("launch_stage", "reboot")


def _check_opengl_and_x(constellation, ssh_client):
    constellation.set_value('sim_launch_msg', 'Testing X and OpenGL')
    constellation.set_value('sim_glx_state', "pending")
    gl_retries = 0
    while True:
        time.sleep(gl_retries * 2)
        gl_retries += 1
        try:
            ping_gl = ssh_client.cmd("bash cloudsim/ping_gl.bash")
            log("bash cloudsim/ping_gl.bash = %s" % ping_gl)
            constellation.set_value('sim_glx_state', "running")
            return
        except Exception as e:
            if gl_retries > 10:
                constellation.set_value('sim_glx_state', "not running")
                constellation.set_value('error', "OpenGL diagnostic failed:"
                                        " %s" % e)
                raise
    # this code should never happen
    return


def deploy_constellation(constellation_name, cloud_provider, machines,
                         openvpn_fname):
    constellation = ConstellationState(constellation_name)

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')

    deploy_fname = _create_deploy_zip_files(constellation_name,
        constellation_directory,
        machines,
        [openvpn_fname])

    constellation.set_value('sim_launch_msg',
                            "waiting for machine to be online")

    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["sim"],
                         "launch_stdout_stderr.log",
                         "packages_setup")

    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["sim"],
                         "cloudsim/setup/deploy_ready",
                         "packages_setup")

    constellation.set_value('sim_launch_msg', "deploying keys")
    ssh_client = _get_ssh_client(constellation_name)
    ssh_client.upload_file(deploy_fname, "cloudsim/deploy.zip")
    ssh_client.cmd('cd cloudsim; unzip -o deploy.zip')

    ssh_client.cmd('bash cloudsim/deploy/deploy.bash')

    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["sim"],
                         "cloudsim/setup/done",
                         "running")


def launch(constellation_name, tags):
    """
    Called by cloudsimd when it receives a launch message
    """
    constellation = ConstellationState(constellation_name)
    use_latest_version = \
        constellation.get_value('configuration') == 'Simulator'

    scripts = {}
    scripts['sim'] = ''

    cloud_provider = tags['cloud_provider']
    constellation_directory = tags['constellation_directory']
    credentials_fname = os.path.join(constellation_directory,
                                     'credentials.txt')

    log("launch constellation name: %s" % constellation_name)

    constellation.set_value("launch_stage", "launch")

    # lets build a list of machines for our constellation
    #
    openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP)  # '11.8.0.2'
    if use_latest_version:
        simulator_image_key = 'ubuntu_1204_x64_cluster'
    else:
        simulator_image_key = 'ubuntu_1204_x64_simulator'

    ip = "127.0.0.1"
    machines = {}
    machines['sim'] = {'hardware': 'cg1.4xlarge',  # 'g2.2xlarge'
                      'software': simulator_image_key,
                      'ip': ip,
                      'security_group': [{'name': 'openvpn',
                                          'protocol': 'udp',
                                          'from_port': 1194,
                                          'to_port': 1194,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ping',
                                           'protocol': 'icmp',
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ssh',
                                           'protocol': 'tcp',
                                          'from_port': 22,
                                          'to_port': 22,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'gzweb',
                                          'protocol': 'tcp',
                                          'from_port': 8080,
                                          'to_port': 8080,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'gzweb websocket',
                                          'protocol': 'tcp',
                                          'from_port': 7681,
                                          'to_port': 7681,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'python notebook',
                                          'protocol': 'tcp',
                                          'from_port': 8888,
                                          'to_port': 8888,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'robot web tools',
                                          'protocol': 'tcp',
                                          'from_port': 9090,
                                          'to_port': 9090,
                                          'cidr': '0.0.0.0/0', },
                                         {'name': 'all tcp on vpn',
                                          'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, },
                                         {'name': 'all udp on vpn',
                                          'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, }
                                         ]
                        }
    constellation.set_value('machines', machines)
    _init_computer_data(constellation_name, machines)
    # Required only if we are not using a prepolated AMI
    if use_latest_version:

        drcsim_package_name = "drcsim"
        ppa_list = []  # ['ubuntu-x-swat/x-updates']
        gpu_driver_list = ['nvidia-current',
                           'nvidia-settings',
                           'nvidia-current-dev',
                           'nvidia-cg-toolkit']

        log("DRC package %s" % drcsim_package_name)
        log("ppas: %s" % ppa_list)
        log("gpu packages %s" % gpu_driver_list)

        ubuntu_sources_repo = get_aws_ubuntu_sources_repo(
                                                      credentials_fname)
        script = get_simulator_script(ubuntu_sources_repo,
                                    drcsim_package_name,
                                    ip,
                                    ros_master_ip=ip,
                                    gpu_driver_list=gpu_driver_list,
                                    ppa_list=ppa_list,
                                    OPENVPN_CLIENT_IP=OPENVPN_CLIENT_IP,
                                    OPENVPN_SERVER_IP=OPENVPN_SERVER_IP)
    else:
        script = ""

    if cloud_provider == "aws":
        acquire_aws_single_server(
                              constellation_name,
                              credentials_ec2=credentials_fname,
                              constellation_directory=constellation_directory,
                              machine_prefix='sim',
                              machine_data=machines['sim'],
                              startup_script=script,
                              tags=tags)
    else:
        raise LaunchException('Unsupported cloud '
                              'provider "%s"' % cloud_provider)

    # Setup the VPN
    ssh_client = _get_ssh_client(constellation_name)
    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname)

    _create_zip_files(constellation_name, constellation_directory, machines)

    deploy_constellation(constellation_name, cloud_provider, machines,
                             openvpn_fname)

    # Required only if we are not using a prepolated AMI
    if use_latest_version:
        # reboot all machines but not router
        machines_to_reboot = machines.keys()
        _reboot_machines(constellation_name, ssh_client,
                         machines_to_reboot, constellation_directory)

    # Waiting for machines to be ready
    machine_names = machines.keys()
    log("_run_machines wait for machines %s : %s" % (constellation_name,
                                                     machine_names))

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       "cloudsim/setup/done",
                       "running")
    log("_run_machines machines %s : %s rebooted!" % (constellation_name,
                                                     machine_names))

    # make sure the monitoring of package setup is complete
    time.sleep(10)

    constellation = ConstellationState(constellation_name)
    for machine_name in machine_names:
        constellation.set_value('%s_aws_state' % machine_name, "running")
        constellation.set_value('%s_launch_state' % machine_name, "running")

    ssh_client = _get_ssh_client(constellation_name)

    log("_run_machines %s: simulator check" % (constellation_name))
    if "sim" in machine_names:
        _check_opengl_and_x(constellation, ssh_client)

        # Install gazebo models locally
        # using a utility script from cloudsim-client-tools
        # careful, we are running as root here?

        # Required only if we are not using a prepolated AMI
        if use_latest_version:
            constellation.set_value('sim_launch_msg', 'Loading Gazebo models')
            ssh_client.cmd("cloudsim/load_gazebo_models.bash")
        constellation.set_value('sim_launch_msg', "complete")

    log("_run_machines %s: wrap up" % (constellation_name))

    constellation.set_value('sim_launch_msg', "complete")
    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name, "complete")
        constellation.set_value('%s_aws_state' % machine_name, "running")
        constellation.set_value('%s_launch_state' % machine_name, "running")
    constellation.set_value("launch_stage", "running")

    return ssh_client.ip


def terminate(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation.set_value('constellation_state', 'terminating')

    machine_name = constellation.get_value('machine_name')

    constellation_directory = constellation.get_value(
                                                    "constellation_directory")
    credentials_fname = os.path.join(constellation_directory,
                                     'credentials.txt')

    constellation.set_value('sim_glx_state', "not running")
    constellation.set_value('gazebo', "not running")
    constellation.set_value('gz_web', "")

    constellation.set_value("%s_state" % machine_name, 'terminating')
    constellation.set_value("%s_launch_msg" % machine_name, 'terminating')
    constellation.set_value("%s_aws_state" % machine_name, 'terminating')
    constellation.set_value("launch_stage", "nothing")

    cloud_provider = constellation.get_value('cloud_provider')
    if cloud_provider == "aws":
        terminate_aws_server(constellation_name, credentials_fname)

    constellation.set_value("%s_state" % machine_name, 'terminated')
    constellation.set_value("%s_launch_msg" % machine_name, 'terminated')
    constellation.set_value("%s_aws_state" % machine_name, 'terminated')

    constellation.set_value('constellation_state', 'terminated')


def __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       ls_cmd,
                       end_state,
                       set_cloud_state=False):

    constellation = ConstellationState(constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= 'running':
        return

    ssh_client = _get_ssh_client(constellation_name)
    q = []
    for machine_name in machine_names:
        key_name = "%s_state" % machine_name
        if set_cloud_state:
            key_name = "%s_aws_state" % machine_name
        q.append(get_ssh_cmd_generator(ssh_client, "timeout -k 1 10 "
                    "cloudsim/find_file_%s.bash %s" % (machine_name, ls_cmd),
                    ls_cmd,
                    constellation,
                    key_name,
                    end_state,
                    max_retries=500))
    empty_ssh_queue(q, sleep=2)


def notify_portal(constellation, task):
    try:
        root_log_dir = '/tmp/cloudsim_logs'

        # Get metadata (team, competition, ...)
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        log("** Portal JSON path: %s ***" % portal_info_fname)
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        log("** Portal JSON file opened ***")
        team = portal_info['team']
        comp = portal_info['event']
        task_num = task['vrc_num']

        log("** Team: %s, Event: %s ***" % (team, comp))

        if task_num < '1' or task_num > '3':
            task_num = '1'
        task_run = task['vrc_id']
        if task_run < '1' or task_run > '5':
            task_run = '1'

        start_time = task['start_time']
        start_task = dateutil.parser.parse(start_time)
        start_task = start_task.strftime("%d/%m/%y %H:%M:%S")

        const = ConstellationState(constellation)
        constellation_dict = get_constellation_data(constellation)
        constellation_directory = constellation_dict['constellation_directory']
        router_ip = const.get_value("router_public_ip")

        task_id = task['ros_launch']
        task_dirname = task_id.split('.')[0]

        # Store in this cloudsim the network and sim logs
        router_key = os.path.join(constellation_directory, 'key-router.pem')

        new_msg = task['task_message'] + '<B> Getting logs</B>'
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        cmd = ('bash /var/www/bin/get_logs.bash %s %s %s'
               % (task_dirname, router_ip, router_key))
        subprocess.check_call(cmd.split())
        log("** Log directory created***")

        # Get the score and falls
        score = '0'
        #falls = 'N/A'
        runtime = 'N/A'
        try:
            p = os.path.join(root_log_dir, task_dirname, 'score.log')
            with open(p) as f:
                log("** score.log found **")
                data = f.read()
                log("** Reading score.log file **")
                lines = data.split('\n')
                last_line = lines[-2]
                log("** Last line: %s **" % last_line)
                score = last_line.split(',')[4]
                #falls = last_line.split(',')[5]

                # Time when the task stopped
                runtime = last_line.split(',')[1]
                log("** All sim score fields parsed **")
        except Exception:
            None

        # Create JSON file with the task metadata
        data = json.dumps({'team': team, 'event': comp, 'task': task_num,
                           'start_time': start_task, 'result': 'Terminated',
                           'runtime': runtime, 'score': score},
                          sort_keys=True, indent=4, separators=(',', ': '))

        log("** JSON data created **")
        with open(os.path.join(root_log_dir, task_dirname,
                               'end_task.json'), 'w') as f:
            f.write(str(data))

        log("** JSON file created ***")

        new_msg = new_msg.replace('Getting logs', 'Creating tar file')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Tar all the log content
        tar_name = team + '_' + comp + '_' + str(task_num)
        tar_name += '_' + str(task_run) + '.tar'

        p = os.path.join(root_log_dir, task_dirname)
        cmd = 'tar cf /tmp/' + tar_name + ' -C ' + p + ' .'
        subprocess.check_call(cmd.split())

        log("** Log directory stored in a tar file ***")

        new_msg = new_msg.replace('Creating tar file',
                                  'Uploading logs to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Send the log to the portal
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        ssh_portal = SshClient('xxx', 'xxx', portal_info['user'],
                               portal_info['hostname'])
        # this is a hack
        ssh_portal.key_fname = config['cloudsim_portal_key_path']

        # Upload the file to the Portal temp dir
        dest = os.path.join('/tmp', tar_name)

        cmd = ('scp -o UserKnownHostsFile=/dev/null'
               '-o StrictHostKeyChecking=no'
               ' -i ' + ssh_portal.key_fname + ' ' + dest + ' ubuntu@' +
               portal_info['hostname'] + ':/tmp')
        log('cmd: %s' % cmd)
        subprocess.check_call(cmd.split())

        # Move the file to the final destination into the Portal
        final_dest = os.path.join(portal_info['final_destination_dir'],
                                  tar_name)
        cmd = 'sudo mv %s %s' % (dest, final_dest)
        ssh_portal.cmd(cmd)

        new_msg = new_msg.replace('Uploading logs to the portal',
                                  'Logs uploaded to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

    except Exception, excep:
        log('notify_portal() Exception: %s' % (repr(excep)))
        raise


class MoniCase(unittest.TestCase):
    """
    Monitors an (existing) constellation. You must read have access to the
    constellation directory.
    """
    def xtest_monitorsim(self):
        constellation_name = 'cx9421ebe4'
        monitor(constellation_name, 1)

    def xtest_ping(self):
        constellation_name = 'cx593c6f5e'
        latency_key = 'sim_latency'
        ssh_ping_proc(constellation_name, '10.0.0.51', latency_key)


class TestSimulator(unittest.TestCase):
    """
    Launches a simulator instance, runs the monitor loop 10 times,
    and terminates it.
    """
    def setUp(self):
        from launch_utils.testing import get_test_path
        from launch_utils.testing import get_boto_path
        from launch_utils.launch_db import get_unique_short_name
        from launch_utils.launch_db import get_cloudsim_version
        from launch_utils.launch_db import init_constellation_data

        print("out=%s" % sys.stdout)
        sys.stdout.flush()

        print("setup")
        self.username = 'tester'
        self.constellation_name = get_unique_short_name("simtest_")

        self.data_dir = get_test_path("simtest")

        # setup CloudSim
        config = {}
        config['machines_directory'] = self.data_dir
        config['cloudsim_version'] = get_cloudsim_version()
        config['boto_path'] = get_boto_path()

        # prepare the launch
        data = {}
        data['cloud_provider'] = 'aws'
        data['configuration'] = 'Simulator-stable'
        data['username'] = self.username

        init_constellation_data(self.constellation_name, data, config)

        print("Launch %s: %s" % (self.constellation_name, data))
        self.sim_ip = launch(self.constellation_name, tags=data)

    def test_sim(self):
        print("test_sim")
        print("ip: %s" % self.sim_ip)
        sweep_count = 10
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.constellation_name, i)

    def tearDown(self):
        print("teardown")
        terminate(self.constellation_name)
        # shutil.rmtree(self.data_dir)


if __name__ == "__main__":
    from launch_utils.testing import get_test_runner
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
