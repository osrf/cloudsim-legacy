from __future__ import print_function

import unittest
import os
import time
import zipfile
import shutil
import json
import subprocess
import dateutil.parser

from shutil import copyfile

from launch_utils.traffic_shaping import  run_tc_command


from launch_utils.monitoring import constellation_is_terminated,\
    monitor_launch_state,  monitor_ssh_ping,\
    monitor_task, monitor_simulator, TaskTimeOut, monitor_gzweb

from launch_utils.softlayer import load_osrf_creds,\
    get_softlayer_path, get_machine_login_info, create_openvpn_key

from launch_utils.launch_db import get_constellation_data, ConstellationState,\
    get_cloudsim_config, log_msg

from launch_utils.testing import get_test_path,\
    get_boto_path, get_test_dir

from launch_utils import get_unique_short_name
from launch_utils.startup_scripts import create_openvpn_client_cfg_file,\
    create_vpc_vpn_connect_file, create_ros_connect_file,\
    create_ssh_connect_file, get_drc_script, get_router_script

from launch_utils.sshclient import SshClient
from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue

import multiprocessing
from launch_utils.sl_cloud import acquire_softlayer_constellation,\
 terminate_softlayer_constellation

from launch_utils.aws import acquire_aws_constellation, LaunchException
from launch_utils.aws import terminate_aws_constellation


ROUTER_IP = '10.0.0.50'
SIM_IP = '10.0.0.51'
FC1_IP = '10.0.0.52'
FC2_IP = '10.0.0.53'
OPENVPN_SERVER_IP = '11.8.0.1'
OPENVPN_CLIENT_IP = '11.8.0.2'

launch_sequence = ["nothing", "os_reload", "launch", "init_router",
                   "init_privates", "zip", "change_ip", "startup",
                   "block_public_ips", "reboot", "running"]


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def start_gzweb(constellation_name):
    log("start_gzweb for %s" % (constellation_name))
    ssh_router = _get_ssh_router(constellation_name)
    o = ssh_router.cmd("cloudsim/start_gzweb.bash")
    log("GZWEB started for %s: %s" % (constellation_name, o))


def stop_gzweb(constellation_name):
    log("stop_gzweb for %s" % (constellation_name))
    ssh_router = _get_ssh_router(constellation_name)
    o = ssh_router.cmd("cloudsim/stop_gzweb.bash")
    log("GZWEB stopped for %s: %s" % (constellation_name, o))


def update(constellation_name):
    """
    Update the constellation software on the servers.
    This function is a plugin function that should be implemented by
    each constellation type
    """

    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu',
                           router_ip)
    for machine in ["sim", "router", "fc1", "fc2", ]:
        constellation.set_value("%s_state" % machine, "packages_setup")
        constellation.set_value("%s_launch_msg" % machine, "updating software")
    try:
        o = ssh_router.cmd("cloudsim/update_constellation.bash")
        log("UPDATE: %s" % o, "toto")
    finally:
        for machine in ["sim", "router", "fc1", "fc2", ]:
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
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    c = "bash cloudsim/start_sim.bash %s %s %s" % (package_name,
                                                   launch_file_name,
                                                   launch_args)
    cmd = c.strip()
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    r = ssh_router.cmd(cmd)
    log('_start_simulator %s' % r)


def _stop_simulator(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_dict = get_constellation_data(constellation_name)
    constellation_directory = constellation_dict['constellation_directory']
    router_ip = constellation.get_value("router_public_ip")
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    r = ssh_router.cmd(cmd)
    log('_stop_simulator %s' % r)


def start_task(constellation_name, task):

    log("START TASK %s for %s" % (constellation_name, task))

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']

    log("** TC COMMAND ***")
    run_tc_command(constellation_name,
                   'sim_machine_name',
                   'key-router',
                   'router_public_ip',
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


def check_for_end_of_task(constellation_name, ssh_router):
    if monitor_task(constellation_name, ssh_router):
        raise TaskTimeOut()


def _get_ssh_router(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    return ssh_router


def ssh_ping_proc(constellation_name, ip, latency_key):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_ssh_ping(constellation_name, ssh_router, ip, latency_key)


def monitor_task_proc(constellation_name):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_task(constellation_name, ssh_router)


def monitor_simulator_proc(constellation_name):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_simulator(constellation_name, ssh_router, "sim_state")


def monitor_gzweb_proc(constellation_name):
    ssh_router = _get_ssh_router(constellation_name)
    monitor_gzweb(constellation_name, ssh_router, "sim_state")


def monitor(constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        log("monitor done for %s" % (constellation_name))
        return True  # stop the monitoring loop

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) < launch_sequence.index('launch'):
        return False  # do it again later

    ssh_router = _get_ssh_router(constellation_name)
    machines = constellation.get_value('machines')

    for machine_name in machines:
        machine_state = constellation.get_value('%s_state' % machine_name)
        monitor_launch_state(constellation_name, ssh_router, machine_state,
                             "cloudsim/dpkg_log_%s.bash" % machine_name,
                             '%s_launch_msg' % machine_name)

    procs = []
    p = multiprocessing.Process(target=monitor_simulator_proc,
                            args=(constellation_name,))
    procs.append(p)

    p = multiprocessing.Process(target=monitor_task_proc,
                                    args=(constellation_name,))
    procs.append(p)

    p = multiprocessing.Process(target=monitor_gzweb_proc,
                            args=(constellation_name,))
    procs.append(p)

    for machine_name, data in machines.iteritems():
        ip = data['ip']
        if machine_name == "router":
            ip = OPENVPN_CLIENT_IP
        p = multiprocessing.Process(target=ssh_ping_proc,
                        args=(constellation_name,
                              ip,
                              '%s_latency' % machine_name))
        procs.append(p)

    for p in procs:
        p.start()

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
    copyfile(os.path.join(constellation_directory, key_short_filename),
             key_fpath)
    os.chmod(key_fpath, 0600)

    fname_ssh_sh = os.path.join(machine_dir,
                                'ssh-%s.bash' % machine_name_prefix)

    file_content = create_ssh_connect_file(key_short_filename, machine_ip)
    with open(fname_ssh_sh, 'w') as f:
        f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    files_to_zip = [key_fpath,
                    fname_ssh_sh, ]

    fname_zip = os.path.join(machine_dir, "%s_%s.zip" % (machine_name_prefix,
                                                         constellation_name))
    create_zip_file(fname_zip, "%s_%s" % (machine_name_prefix,
                                          constellation_name), files_to_zip)
    return fname_zip


def _create_deploy_zip_files(constellation_name,
                     constellation_directory,
                     machines,
                     files=[]):

    private_network_interface_name = machines['router']['public_network_itf']
    public_network_interface_name = machines['router']['private_network_itf']

    restore_default_tc_rules = ""

    if public_network_interface_name:
        restore_default_tc_rules += """
    # Restore the default tc rules
    sudo vrc_init_tc.py """ + public_network_interface_name + """

    """

    if private_network_interface_name:
        restore_default_tc_rules += """
    sudo vrc_init_tc.py """ + private_network_interface_name + """
"""

    ssh_scripts = ""

    for machine_name, data in machines.iteritems():
        ip = data['ip']
        ssh_scripts += """

#
# interactive ssh script
#
cat <<DELIM > /home/ubuntu/cloudsim/ssh-""" + machine_name + """.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-""" + machine_name+ """.pem ubuntu@""" + ip + """ \$1 \$2 \$3 \$4 \$5 \$6
DELIM
chmod +x /home/ubuntu/cloudsim/ssh-""" + machine_name + """.bash
# --------------------------------------------

#
# dpkg log script
#
cat <<DELIM > /home/ubuntu/cloudsim/dpkg_log_""" + machine_name+ """.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-""" + machine_name+ """.pem ubuntu@""" + ip + """  "tail -1 /var/log/dpkg.log"
DELIM
chmod +x /home/ubuntu/cloudsim/dpkg_log_""" + machine_name+ """.bash
# --------------------------------------------

#
# find file script
#
cat <<DELIM > /home/ubuntu/cloudsim/find_file_""" + machine_name+ """.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-""" + machine_name+ """.pem ubuntu@""" + ip + """  "ls \$1"
DELIM
chmod +x /home/ubuntu/cloudsim/find_file_""" + machine_name+ """.bash
# --------------------------------------------

#
# reboot script
#
cat <<DELIM > /home/ubuntu/cloudsim/reboot_""" + machine_name+ """.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-""" + machine_name+ """.pem ubuntu@""" + ip + """ "sudo reboot"

DELIM
chmod +x /home/ubuntu/cloudsim/reboot_""" + machine_name+ """.bash


#
# gzweb
#

# ----------------------------------------------------------------------------
cat <<DELIM > /home/ubuntu/cloudsim/update_constellation.bash
#!/bin/bash

# update local packages on the router
# sudo cloudsim/update_drcsim.bash

. /home/ubuntu/cloudsim/gzweb/deploy.sh

DELIM
chmod +x /home/ubuntu/cloudsim/update_constellation.bash

# ----------------------------------------------------------------------------
cat <<DELIM > /home/ubuntu/cloudsim/start_gzweb.bash
#!/bin/bash
logfile=/home/ubuntu/cloudsim/start_gzweb.log
exec >> \$logfile 2>&1

echo "#"
echo "#"
date

# sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 80 -j REDIRECT --to-port 8080

/home/ubuntu/cloudsim/gzweb/start_gzweb.sh &

sudo start cloudsim_notebook

DELIM
chmod +x /home/ubuntu/cloudsim/start_gzweb.bash

# ----------------------------------------------------------------------------
cat <<DELIM > /home/ubuntu/cloudsim/stop_gzweb.bash
#!/bin/bash
logfile=/home/ubuntu/cloudsim/stop_gzweb.log.log
exec >> \$logfile 2>&1

echo "#"
echo "#"
date

/home/ubuntu/cloudsim/gzweb/stop_gzweb.sh

sudo stop cloudsim_notebook

DELIM

chmod +x /home/ubuntu/cloudsim/stop_gzweb.bash

# ----------------------------------------------------------------------------
cat <<DELIM > /home/ubuntu/cloudsim/ping_gzweb.bash
#!/bin/bash

# Fails if gzbridge is not running, returns 0 otherwize
ps aux | grep ws_server  | grep -v grep

DELIM
chmod +x /home/ubuntu/cloudsim/ping_gzweb.bash




"""

    # now create a script that contains all the scripts together
    deploy_script = """#!/bin/bash
# Exit on error
set -ex
# Redirect everybody's output to a file
logfile=/home/ubuntu/cloudsim/deploy.log
exec > $logfile 2>&1

# copy keys to cloudsim directory
cp /home/ubuntu/cloudsim/deploy/*.pem /home/ubuntu/cloudsim

""" + ssh_scripts + """


cat <<DELIM > /home/ubuntu/cloudsim/ping_gl.bash
#!/bin/bash

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """  "DISPLAY=localhost:0 timeout -k 1 5 glxinfo"
DELIM
chmod +x /home/ubuntu/cloudsim/ping_gl.bash

# --------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/stop_sim.bash
#!/bin/bash
sudo stop vrc_netwatcher
kill -9 \$(ps aux | grep vrc_netwatcher | awk '{print \$2}') || true
sudo stop vrc_bytecounter
sudo redis-cli set vrc_target_outbound_latency 0
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """  "bash cloudsim/stop_sim.bash"
sudo iptables -F FORWARD

# Stop the latency injection
sudo stop vrc_controller_private
sudo stop vrc_controller_public

""" + restore_default_tc_rules + """

DELIM
chmod +x /home/ubuntu/cloudsim/stop_sim.bash


# --------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/ping_gazebo.bash
#!/bin/bash

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no \
 -i /home/ubuntu/cloudsim/key-sim.pem -n ubuntu@""" + SIM_IP + """ \
 ". /usr/share/drcsim/setup.sh; timeout -k 1 5 gztopic list"


DELIM
chmod +x /home/ubuntu/cloudsim/ping_gazebo.bash
# --------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/start_sim.bash
#!/bin/bash

# Just rename the old network usage file
sudo mv /tmp/vrc_netwatcher_usage.log /tmp/vrc_netwatcher_usage_\`date | tr -d ' '\`.log || true

# Stop the latency injection
sudo stop vrc_controller_private
sudo stop vrc_controller_public

""" + restore_default_tc_rules + """

sudo iptables -F FORWARD
sudo stop vrc_netwatcher
kill -9 \$(ps aux | grep vrc_netwatcher | awk '{print \$2}') || true
sudo stop vrc_bytecounter
sudo start vrc_netwatcher
if ! ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """  "nohup bash cloudsim/start_sim.bash \$1 \$2 \$3 > ssh_start_sim.out 2> ssh_start_sim.err < /dev/null"; then
  echo "[router start_sim.bash] simulator start_sim.bash returned non-zero"
  exit 1
fi

DELIM
chmod +x /home/ubuntu/cloudsim/start_sim.bash

# --------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/copy_net_usage.bash
#!/bin/bash

# 1. Copy the directory containing the JSON task file and the network usage to the simulator
# 2. Run a script on the simulator that zip all the log files and send them to the portal
USAGE="Usage: copy_net_usage <task_dirname> <zipname>"

if [ \$# -ne 2 ]; then
  echo \$USAGE
  exit 1
fi

echo --- >> copy_net_usage.log 2>&1

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """  mkdir -p /home/ubuntu/cloudsim/logs >> copy_net_usage.log 2>&1

TASK_DIRNAME=\$1
if [ -f /tmp/vrc_netwatcher_usage.log ];
then
  cp /tmp/vrc_netwatcher_usage.log \$TASK_DIRNAME >> copy_net_usage.log 2>&1
fi
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem -r /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME ubuntu@""" + SIM_IP + """ :/home/ubuntu/cloudsim/logs/ >> copy_net_usage.log 2>&1

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """  bash /home/ubuntu/cloudsim/send_to_portal.bash \$1 \$2 /home/ubuntu/ubuntu-portal.key vrcportal-test.osrfoundation.org >> copy_net_usage.log 2>&1
DELIM
chmod +x /home/ubuntu/cloudsim/copy_net_usage.bash

# --------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/get_sim_logs.bash
#!/bin/bash

# Get state.log and score.log from the simulator 

USAGE="Usage: get_sim_logs.bash <task_dirname>"

if [ \$# -ne 1 ]; then
  echo \$USAGE
  exit 1
fi

TASK_DIRNAME=\$1

mkdir -p /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME

# Copy the log files
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@""" + SIM_IP + """ :/tmp/\$TASK_DIRNAME/* /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME || true

# Copy the network usage
if [ -f /tmp/vrc_netwatcher_usage.log ];
then
  cp /tmp/vrc_netwatcher_usage.log /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME >> copy_net_usage.log 2>&1
fi

DELIM
chmod +x /home/ubuntu/cloudsim/get_sim_logs.bash

# ----------------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/get_network_usage.bash
#!/bin/bash

#
# wall or sim clock, wall or sim clock, uplink downlink
# space is the separator
tail -1 /tmp/vrc_netwatcher_usage.log

DELIM
chmod +x /home/ubuntu/cloudsim/get_network_usage.bash

# ----------------------------------------------------

cat <<DELIM > /home/ubuntu/cloudsim/get_score.bash
#!/bin/bash

. /usr/share/drcsim/setup.sh
# rostopic echo the last message of the score
timeout -k 1 10 rostopic echo -p /vrc_score -n 1


DELIM
chmod +x /home/ubuntu/cloudsim/get_score.bash


# configure openvpn
sudo cp /home/ubuntu/cloudsim/deploy/openvpn.key /etc/openvpn/static.key
sudo chmod 644 /etc/openvpn/static.key
sudo service openvpn restart

# chechck that the tunnel interface is up
sudo ifconfig

"""

# import apt
#
# cache = apt.Cache()
# p = cache['drcsim']
# v = p.installed.version
# d = p.description

# pkg = cache['python-apt'] # Access the Package object for python-apt
# print 'python-apt is trusted:', pkg.candidate.origins[0].trusted
#
# # Mark python-apt for install
# pkg.mark_install()
#
# print 'python-apt is marked for install:', pkg.marked_install
#
# print 'python-apt is (summary):', pkg.candidate.summary
#
# # Now, really install it
# cache.commit()

    # constellation = ConstellationState(constellation_name)
    deploy_dir = os.path.join(constellation_directory, "deploy")
    os.makedirs(deploy_dir)

    deploy_script_fname = os.path.join(deploy_dir, "deploy.bash")
    with open(deploy_script_fname, 'w') as f:
        f.write(deploy_script)

    files_to_zip = [fi for fi in files]
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


def create_router_zip(router_ip, constellation_name, key_prefix,
                      constellation_directory):
    """ create router zip file with keys
     This file is kept on the server and provides the user with:
      - key file for ssh access to the router
      - openvpn key
      - scripts to connect with ssh, openvpn, ROS setup
    """

    router_machine_dir = os.path.join(constellation_directory, "router")
    os.makedirs(router_machine_dir)

    # copy router-key into router directory
    router_key_short_filename = '%s.pem' % key_prefix  # 'key-router'
    router_key_path = os.path.join(router_machine_dir,
                                   router_key_short_filename)
    copyfile(os.path.join(constellation_directory, router_key_short_filename),
             router_key_path)
    os.chmod(router_key_path, 0600)

    vpn_key_short_filename = 'openvpn.key'
    vpnkey_fname = os.path.join(router_machine_dir, vpn_key_short_filename)
    copyfile(os.path.join(constellation_directory, vpn_key_short_filename),
             vpnkey_fname)
    os.chmod(vpnkey_fname, 0600)

    # create open vpn config file
    file_content = create_openvpn_client_cfg_file(router_ip,
                    client_ip=OPENVPN_CLIENT_IP, server_ip=OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(router_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)

    fname_start_vpn = os.path.join(router_machine_dir, "start_vpn.bash")
    file_content = create_vpc_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755)

    fname_ros = os.path.join(router_machine_dir, "ros.bash")
    file_content = create_ros_connect_file(machine_ip=OPENVPN_CLIENT_IP,
                                           master_ip=SIM_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)

    fname_ssh_sh = os.path.join(router_machine_dir, 'ssh-router.bash')
    file_content = create_ssh_connect_file(router_key_short_filename,
                                           router_ip)
    with open(fname_ssh_sh, 'w') as f:
        f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    # wait (if necessary) for openvpn key to have been generated
    #creating zip for admin and officer users
    files_to_zip = [router_key_path,
                    fname_start_vpn,
                    fname_ssh_sh,
                    fname_vpn_cfg,
                    vpnkey_fname,
                    fname_ros, ]
    router_fname_zip = os.path.join(router_machine_dir,
                                    "router_%s.zip" % constellation_name)
    create_zip_file(router_fname_zip,
                            "router_%s" % constellation_name, files_to_zip)

    # create another zip file, this time for users only
    # (without the ssh key or the ssh-router.bash)
    files_to_zip = [fname_start_vpn,
                    fname_vpn_cfg,
                    vpnkey_fname,
                    fname_ros, ]
    router_user_fname_zip = os.path.join(router_machine_dir,
                                    "user_router_%s.zip" % constellation_name)
    create_zip_file(router_user_fname_zip,
                                "router_%s" % constellation_name, files_to_zip)
    return router_fname_zip, router_user_fname_zip


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

    for machine_name, machine_data in machines.iteritems():
        machine_key_prefix = 'key-%s' % (machine_name)
        msg_key = '%s_launch_msg' % machine_name
        zip_ready_key = "%s_zip_file" % machine_name
        zip_fname = os.path.join(constellation_directory,
                                 "%s.zip" % machine_name)
        zip_user_fname = os.path.join(constellation_directory,
                                 "user_%s.zip" % machine_name)

        constellation.set_value(msg_key, 'creating zip file')
        if machine_name == "router":
            router_ip = constellation.get_value("router_public_ip")
            router_zip_fname, router_zip_user_fname = create_router_zip(
                                                    router_ip,
                                                    constellation_name,
                                                    machine_key_prefix,
                                                    constellation_directory)
            shutil.copy(router_zip_fname, zip_fname)
            shutil.copy(router_zip_user_fname, zip_user_fname)
        else:
            constellation.set_value(msg_key, 'creating zip files')
            ip = machine_data['ip']
            machine_zip_fname = create_private_machine_zip(machine_name,
                                               ip,
                                               constellation_name,
                                               constellation_directory,
                                               machine_key_prefix)
            shutil.copy(machine_zip_fname, zip_fname)
            if machine_name != "sim":
                shutil.copy(machine_zip_fname, zip_user_fname)
        constellation.set_value(zip_ready_key, 'ready')

    constellation.set_value("launch_stage", "zip")


def _reboot_machines(constellation_name,
                     ssh_router,
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

    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name,
                                    "Rebooting after software installation")
        constellation.set_value('%s_aws_state' % machine_name, "rebooting")

    for machine_name in machine_names:
        ssh_router.cmd("cloudsim/reboot_%s.bash" % machine_name)
    log("waiting before connecting after reboot")
    time.sleep(20)
    constellation.set_value("launch_stage", "reboot")


def _check_opengl_and_x(constellation, ssh_router):
    constellation.set_value('sim_launch_msg', 'Testing X and OpenGL')
    constellation.set_value('sim_glx_state', "pending")
    gl_retries = 0
    while True:
        time.sleep(gl_retries * 2)
        gl_retries += 1
        try:
            ping_gl = ssh_router.cmd("bash cloudsim/ping_gl.bash")
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


def _run_machines(constellation_name, machine_names, constellation_directory):
    log("_run_machines wait for machines %s : %s" % (constellation_name,
                                                     machine_names))

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       machine_names,
                       "cloudsim/setup/done",
                       "running",
                       True)
    log("_run_machines machines %s : %s rebooted!" % (constellation_name,
                                                     machine_names))

    # make sure the monitoring of package setup is complete
    time.sleep(10)

    constellation = ConstellationState(constellation_name)
    for machine_name in machine_names:
        constellation.set_value('%s_aws_state' % machine_name, "running")
        constellation.set_value('%s_launch_state' % machine_name, "running")

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)

    log("_run_machines %s: simulator check" % (constellation_name))
    if "sim" in machine_names:
        _check_opengl_and_x(constellation, ssh_router)

        # Install gazebo models locally
        # using a utility script from cloudsim-client-tools
        # careful, we are running as root here?
        constellation.set_value('sim_launch_msg', 'Loading Gazebo models')
        ssh_router.cmd("cloudsim/ssh-sim.bash "
                       "cloudsim/load_gazebo_models.bash")
        constellation.set_value('sim_launch_msg', "complete")

    log("_run_machines %s: wrap up" % (constellation_name))

    constellation.set_value('router_launch_msg', "complete")
    for machine_name in machine_names:
        constellation.set_value('%s_launch_msg' % machine_name, "complete")
        constellation.set_value('%s_aws_state' % machine_name, "running")
        constellation.set_value('%s_launch_state' % machine_name, "running")
    constellation.set_value("launch_stage", "running")


def deploy_constellation(constellation_name, cloud_provider, machines):

    constellation = ConstellationState(constellation_name)

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    router_ip = constellation.get_value('router_public_ip')
    ssh_router = SshClient(constellation_directory,
                           'key-router',
                           'ubuntu',
                           router_ip)
    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname)

    _create_zip_files(constellation_name, constellation_directory, machines)

    deploy_fname = _create_deploy_zip_files(constellation_name,
        constellation_directory,
        machines,
        [openvpn_fname])

    constellation.set_value('router_launch_msg',
                            "waiting for machine to be online")
    constellation.set_value('sim_launch_msg',
                            "waiting for router access")
    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["router"],
                         "launch_stdout_stderr.log",
                         "packages_setup")

    constellation.set_value('router_launch_msg',
                            "waiting for base packages to be installed")
    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["router"],
                         "cloudsim/setup/deploy_ready",
                         "packages_setup")
    constellation.set_value('router_launch_msg', "deploying keys")
    ssh_router.upload_file(deploy_fname, "cloudsim/deploy.zip")
    ssh_router.cmd('cd cloudsim; unzip deploy.zip')

    ssh_router.cmd('bash cloudsim/deploy/deploy.bash')

#     cmd = ("nohup sudo bash cloudsim/deploy/deploy.bash "
#             "> ssh_deploy.out 2> ssh_deploy.err < /dev/null &")
#     ssh_router.cmd(cmd)

    __wait_for_find_file(constellation_name,
                         constellation_directory,
                         ["router"],
                         "cloudsim/setup/done",
                         "running")

    # reboot fc1, fc2 and sim (but not router)
    machines_to_reboot = machines.keys()
    machines_to_reboot.remove('router')

    _reboot_machines(constellation_name, ssh_router,
                     machines_to_reboot, constellation_directory)

    _run_machines(constellation_name, machines.keys(), constellation_directory)
    constellation.set_value("launch_stage", "running")


def launch(username, config, constellation_name, tags,
           constellation_directory, credentials_override=None):
    """
    Called by cloudsimd when it receives a launch message
    """
    cloud_provider = "aws"
    has_fc1 = False
    has_fc2 = False

    if "OSRF" in config:
        cloud_provider = "softlayer"
    if "FC" in config:
        has_fc1 = True

    router_public_network_itf = "eth0"
    router_private_network_itf = None
    if cloud_provider == "softlayer":
        router_public_network_itf = "bond1"
        router_private_network_itf = "bond0"
    log("launch constellation name: %s" % constellation_name)

    constellation = ConstellationState(constellation_name)
    constellation.set_value("launch_stage", "launch")

    drcsim_package_name = "drcsim"
    ppa_list = []  # ['ubuntu-x-swat/x-updates']
    gpu_driver_list = ['nvidia-current',
                       'nvidia-settings',
                       'nvidia-current-dev',
                       'nvidia-cg-toolkit']

    if config.find("nightly") >= 0:
        drcsim_package_name = "drcsim-nightly"
    elif config.find("nvidia 319") >= 0:
        ppa_list = ['xorg-edgers/ppa']
        gpu_driver_list = ["nvidia-319", 'nvidia-settings']

    log("DRC package %s" % drcsim_package_name)
    log("ppas: %s" % ppa_list)
    log("gpu packages %s" % gpu_driver_list)

    #
    # lets build a list of machines for our constellation
    #
    openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP)  # '11.8.0.2'
    private_subnet = '10.0.0.0/24'

    machines = {}
    machines['router'] = {'hardware': 'm1.large',    # 't1.micro',
                      'software': 'ubuntu_1204_x64',
                      'ip': ROUTER_IP,   # 'startup_script': router_script,
                      'public_network_itf': router_public_network_itf,
                      'private_network_itf': router_private_network_itf,
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
                                          'from_port': 22,   # ssh
                                          'to_port': 22,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'all udp on private sub',
                                           'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                          {'name': 'all tcp on private sub',
                                          'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
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
                                         ]
                          }
# VPN_PRIVATE_SUBNET = '10.0.0.0/24'
#
#             openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP) '11.8.0.2'
#             sg.authorize('icmp', -1, -1, openvpn_client_addr)
#             sg.authorize('tcp', 0, 65535, openvpn_client_addr)
#             sg.authorize('udp', 0, 65535, openvpn_client_addr)

    machines['sim'] = {'hardware': 'cg1.4xlarge',
                  'software': 'ubuntu_1204_x64_cluster',
                  'ip': SIM_IP,
                      'security_group': [{'protocol': 'icmp',  # ping
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                         {'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                         {'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': private_subnet, },
                                         {'protocol': 'tcp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, },
                                         {'protocol': 'udp',
                                          'from_port': 0,
                                          'to_port': 65535,
                                          'cidr': openvpn_client_addr, }]
                    }

    if has_fc1:
        machines['fc1'] = {'hardware': 'cg1.4xlarge',
                  'software': 'ubuntu_1204_x64_cluster',
                  'ip': FC1_IP,
                    }
    if has_fc2:
        machines['fc2'] = {'hardware': 'cg1.4xlarge',
                  'software': 'ubuntu_1204_x64_cluster',
                  'ip': FC2_IP,
                    }

    _init_computer_data(constellation_name, machines)

    ros_master_ip = SIM_IP

    scripts = {}
    scripts['router'] = get_router_script(router_public_network_itf,
                                      router_private_network_itf,
                                      ROUTER_IP,
                                      SIM_IP,
                                      drcsim_package_name,
                                      OPENVPN_SERVER_IP,
                                      OPENVPN_CLIENT_IP)

    scripts['sim'] = get_drc_script(drcsim_package_name,
                                SIM_IP,
                                ros_master_ip,
                                gpu_driver_list,
                                ppa_list,
                                OPENVPN_CLIENT_IP,
                                ROUTER_IP)

    fc1_script = get_drc_script(drcsim_package_name,
                                    FC1_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list,
                                    OPENVPN_CLIENT_IP,
                                    ROUTER_IP)

    fc2_script = get_drc_script(drcsim_package_name,
                                    FC2_IP,
                                    ros_master_ip,
                                    gpu_driver_list,
                                    ppa_list,
                                    OPENVPN_CLIENT_IP,
                                    ROUTER_IP)

    if has_fc1:
        scripts['fc1'] = fc1_script

    if has_fc2:
        scripts['fc2'] = fc2_script

    cs_cfg = get_cloudsim_config()
    if cloud_provider == "softlayer":
        credentials_fname = cs_cfg['softlayer_path']
        if credentials_override:
            credentials_fname = credentials_override
        log("softlayer %s" % credentials_fname)
        constellation_prefix = config.split()[-1]
        log("constellation_prefix %s" % constellation_prefix)
        partial_deploy = False
        if config.find("partial") > 0:
            partial_deploy = True
        log("partial deploy: %s (only sim and router)" % partial_deploy)

        acquire_softlayer_constellation(constellation_name,
                                    constellation_directory,
                                    partial_deploy,
                                    constellation_prefix,
                                    credentials_fname,
                                    tags,
                                    scripts['router'],
                                    scripts['sim'],
                                    fc1_script,
                                    fc2_script)

    if cloud_provider == "aws":
        credentials_fname = cs_cfg['boto_path']
        if credentials_override:
            credentials_fname = credentials_override
        log("credentials_ec2 %s" % credentials_fname)
        acquire_aws_constellation(constellation_name,
                                  credentials_fname,
                                  machines,
                                  scripts,
                                  tags)

    deploy_constellation(constellation_name, cloud_provider, machines,)


def terminate(constellation_name, credentials_override=None):
    constellation = ConstellationState(constellation_name)
    machines = constellation.get_value('machines')

    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('sim_glx_state', "not running")
    constellation.set_value('gazebo', "not running")
    constellation.set_value('gz_web', "")

    for machine_name in machines:
        constellation.set_value("%s_state" % machine_name, 'terminating')
        constellation.set_value("%s_launch_msg" % machine_name, 'terminating')
        constellation.set_value("%s_aws_state" % machine_name, 'terminating')

    cs_cfg = get_cloudsim_config()
    constellation.set_value("launch_stage", "nothing")

    if not "OSRF" in constellation_name:
        credentials_fname = cs_cfg['boto_path']
        if credentials_override:
            credentials_fname = credentials_override
        terminate_aws_constellation(constellation_name, credentials_fname)
    else:
        credentials_fname = cs_cfg['softlayer_path']
        if credentials_override:
            credentials_fname = credentials_override
        partial = False
        constellation_prefix = constellation_name.split('_')[-1]
        terminate_softlayer_constellation(constellation_name,
                       constellation_prefix,
                       partial,
                       credentials_fname)

    for machine_name in machines:
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

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    q = []
    for machine_name in machine_names:
        key_name = "%s_state" % machine_name
        if set_cloud_state:
            key_name = "%s_aws_state" % machine_name
        q.append(get_ssh_cmd_generator(ssh_router, "timeout -k 1 10 "
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
        run = task['vrc_id']
        if run < '1' or run > '5':
            run = '1'

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
        tar_name = (team + '_' + comp + '_' + str(task_num) + '_' + str(run) +
                    '.tar')
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


class MonitorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxb49a97c4'
        cred = get_softlayer_path()

        monitor(user, const, cred)


class VrcCase(object):  # (unittest.TestCase):

    def atest_zip_create(self):
        constellation_name = "toto"
        constellation_directory = os.path.join(get_test_path("zip_test"))
        router_ip = '50.23.225.173'
        create_router_zip(router_ip,
                          constellation_name,
                          constellation_directory)
        create_private_machine_zip("fc1",
                                     FC1_IP,
                                     constellation_name,
                                     constellation_directory)

#     def test_script(self):
#         s = get_sim_script('drcsim')
#         print(s)
#         print("")

    def atest_launch(self):

        constellation_prefix = "02"
        #launch_stage = None  # use the current stage

        #launch_stage = "nothing"
        #launch_stage = "os_reload"
        # "nothing", "os_reload", "init_router", "init_privates", "zip",
        # "change_ip", "startup", "reboot", "running"
        launch_stage = "running"

        self.constellation_name = 'test_vrc_contest_%s' % constellation_prefix
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer = get_softlayer_path()
        CONFIGURATION = 'vrc_contest'
        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name = get_unique_short_name(test_name + "_")
            P = os.path.join(get_test_path(test_name), self.constellation_name)
            self.constellation_directory = os.path.abspath(P)
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            p = os.path.join(get_test_path(test_name), self.constellation_name)
            self.constellation_directory = os.path.abspath(p)

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory",
                                    self.constellation_directory)
        constellation.set_value("configuration", 'vrc_contest')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        self.tags = {'TestCase': CONFIGURATION,
                     'configuration': CONFIGURATION,
                     'constellation': self.constellation_name,
                     'user': self.username,
                     'GMT': "now"}

        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)
        config = "OSRF VRC Constellation %s" % constellation_prefix

        launch(self.username,
               config,
               self.constellation_name,
               self.tags,
               self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.username, self.constellation_name, i)
            time.sleep(1)

        terminate(self.constellation_name, self.credentials_softlayer)

    def atest_monitor(self):

        self.constellation_name = "cxf44f7040"
        self.username = "toto@osrfoundation.org"
        self.credentials_softlayer = get_softlayer_path()

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.username, self.constellation_name, i)
            time.sleep(1)

    def stest_ubuntu_user_on_sim_from_router(self):

        constellation = ConstellationState('test_vrc_contest_toto')

        constellation_directory = constellation.get_value(
                                                    "constellation_directory")
        router_ip = constellation.get_value("router_public_ip")
        ssh_router = SshClient(constellation_directory,
                               "key-router",
                               'ubuntu',
                               router_ip)
        credentials_softlayer = get_softlayer_path()
        osrf_creds = load_osrf_creds(credentials_softlayer)

        pub_ip, ip, password = get_machine_login_info(osrf_creds, "sim-01")
        log("setting up ubuntu user on simulator machine "
            "[%s / %s]" % (pub_ip, ip))
        cmd = ("cd cloudsim; ./auto_ubuntu.bash "
            "%s %s ./key-sim.pem.pub" % (ip, password))
        log(cmd)
        out = ssh_router.cmd(cmd)
        log(out)

    def tearDown(self):
        unittest.TestCase.tearDown(self)


class AwsCase(unittest.TestCase):

    def setUp(self):
        print("setup")

        self.constellation_name = "test_xxx"
        print(self.constellation_name)

        self.config = 'AWS DRC with FC'  # "AWS DRC"
        self.username = "test@osrfoundation.org"

        print("%s %s" % (self.config, self.constellation_name))

        self.constellation_directory = os.path.join(get_test_dir(),
                                               self.constellation_name)
        print(self.constellation_directory)

        if os.path.exists(self.constellation_directory):
            bk_name = self.constellation_directory + get_unique_short_name('_')
            print("backup: %s" % bk_name)
            os.rename(self.constellation_directory, bk_name)
        os.makedirs(self.constellation_directory)

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_directory",
                                self.constellation_directory)

        constellation.set_value('username', self.username)
        constellation.set_value('constellation_name', self.constellation_name)
        constellation.set_value('gmt', 'gmt')
        constellation.set_value('configuration', self.config)
        constellation.set_value('constellation_directory',
                                self.constellation_directory)
        constellation.set_value('error', '')

        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

    def test_launch(self):
        print("test_launch")
        tags = {}
        p = get_boto_path()
        launch(self.username,
               self. config,
               self.constellation_name,
               tags,
               self.constellation_directory,
               credentials_override=p)
        print("launched")

        for i in range(50):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

        constellation = ConstellationState(self.constellation_name)
        self.assert_(constellation.get_value('gazebo') == "not running", "!")

        task = {}
        task['latency'] = 0
        task['uplink_data_cap'] = 0
        task['downlink_data_cap'] = 0
        task['ros_package'] = "atlas_utils"
        task['ros_launch'] = "vrc_task_1.launch"
        task['ros_args'] = ""
        task['timeout'] = 60

        start_task(self.constellation_name, task)

        for i in range(3):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

        self.assert_(constellation.get_value('gazebo') == "running", "!")

        for i in range(20):
            print('monitor %s' % i)
            monitor(self.constellation_name, i)
            time.sleep(5)

    def tearDown(self):
        print("teardown")

        terminate(self.constellation_name,
                  credentials_override=get_boto_path())
        constellation = ConstellationState(self.constellation_name)
        constellation.set_value('constellation_state', 'terminated')
        log("Deleting %s from the database" % self.constellation_name)
        constellation.expire(1)


class SumCase(unittest.TestCase):

    def atestO(self):
        constellation_name = 'toto'
        p = os.path.join(os.path.expanduser('~'), 'tests', 'toto')
        constellation_directory = p

        # os.makedirs(constellation_directory)
        constellation_name 
        machines = ['router', 'sim']
        zip_fname = _create_deploy_zip_files(constellation_name,
                                 constellation_directory,
                                 machines)
        self.assertTrue(os.path.exists(zip_fname), "not there")

    def xtest_deploy(self):
        constellation_name = 'cx11fc02b4'
        deploy_constellation(constellation_name)


class MoniCase(unittest.TestCase):

    def atest_monitorsim(self):
        constellation_name = 'cx8db055c6'
        x = monitor_simulator_proc(constellation_name)
        print("monitor_simulator_proc %s" % x)

    def ztest_ping(self):
        constellation_name = 'cx593c6f5e'
        latency_key = 'sim_latency'
        ssh_ping_proc(constellation_name, '10.0.0.51', latency_key)

if __name__ == "__main__":
#    xmlTestRunner = get_test_runner()
#    unittest.main(testRunner=xmlTestRunner)
    n = 'cxceaae4dc'
    i = 0
#    monitor(n, i)
    monitor_gzweb_proc(n)