from __future__ import print_function

import shutil
import os

from launch_db import ConstellationState, log_msg
from softlayer import load_osrf_creds, get_machine_login_info,\
    wait_for_server_reloads, create_ssh_key, reload_servers,\
    setup_ssh_key_access
from sshclient import clean_local_ssh_key_entry
from sshclient import SshClient
from ssh_queue import get_ssh_cmd_generator, empty_ssh_queue
from softlayer import shutdown_public_ips, create_openvpn_key,\
    enable_public_ips, get_active_transaction
import softlayer


ROUTER_IP = '10.0.0.50'


class ReloadOsCallBack(object):
    def __init__(self, constellation_name, machines_dict):
        self.constellation_name = constellation_name
        self.machines_dict = machines_dict
        self.constellation_state = ConstellationState(constellation_name)

    def callback(self, machine_name, state):
        msg_key = self.machines_dict[machine_name]
        log("[%s] %s [%s] %s" % (self.constellation_name,
                                 machine_name, msg_key, state))

        self.constellation_state.set_value(msg_key, state)

launch_sequence = ["nothing", "os_reload", "init", "zip",  "change_ip",
                   "startup", "reboot", "running"]


def log(msg, channel=__name__, severity='debug'):
    log_msg(msg, channel, severity)


def acquire_dedicated_sl_server(constellation_name,
                           osrf_creds_fname,
                           constellation_directory):
    """
    Acquire a dedicated SoftLayer machine
    """
    constellation = ConstellationState(constellation_name)
    constellation_prefix = constellation_name.split("OSRF_CloudSim_")[1]

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init'):
        return

    if os.path.exists(constellation_directory):
        shutil.rmtree(constellation_directory)
    os.makedirs(constellation_directory)

    machines_dict = {'cs-%s' % constellation_prefix: 'simulation_launch_msg'}

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)

    # wait
    wait_for_server_reloads(osrf_creds, machines_dict.keys(),
                            reload_monitor.callback)
    constellation.set_value('simulation_aws_state', 'running')
    constellation.set_value('simulation_state', 'packages_setup')
    name = "cs-%s" % constellation_prefix

    pub_ip, priv_ip, password = get_machine_login_info(osrf_creds, name)
    log("ubuntu user setup for machine cs %s [%s / %s] " % (name, pub_ip,
                                                            priv_ip))
    # dst_dir = os.path.abspath('.')

    log("machine details cs %s %s : %s" % (name, pub_ip, password))
    # __add_ubuntu_user_to_router(pub_ip, password, constellation_directory,
    #                          'key-cs')
    key_prefix = 'key-cs'
    clean_local_ssh_key_entry(pub_ip)
    create_ssh_key(key_prefix, constellation_directory)
    # setup a ubuntu sudoer no password user with an ssh key
    pub_key_path = os.path.join(constellation_directory,
                                       "%s.pem.pub" % key_prefix)
    setup_ssh_key_access(pub_ip, password, pub_key_path)
    priv_key_path = os.path.join(constellation_directory,
                                        "%s.pem" % key_prefix)
    log("ssh -i %s ubuntu@%s" % (priv_key_path, pub_ip))

    constellation.set_value("launch_stage", "init")
    return pub_ip, pub_key_path, priv_key_path


def terminate_dedicated_sl_server(constellation_name, machine_name,
                                  osrf_creds_fname):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'os_reload'):
        return

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    # compute the softlayer machine names

    machine_names = [machine_name]
    pub_ip, priv_ip, password = get_machine_login_info(osrf_creds,
                                                       machine_names[0])
    log("reload os for machine %s [%s / %s] password %s " % (machine_names[0],
                                                             pub_ip, priv_ip,
                                                             password))
    reload_servers(osrf_creds, machine_names)
    constellation.set_value("launch_stage", "os_reload")


def acquire_softlayer_constellation(constellation_name,
                                    constellation_directory,
                                    partial_deploy,
                                    constellation_prefix,
                                    credentials_softlayer,
                                    tags,
                                    ros_master_ip,
                                    router_script,
                                    sim_script,
                                    fc1_script,
                                    fc2_script):

    _wait_for_constellation_reload(constellation_name,
                                   constellation_prefix,
                                   partial_deploy, credentials_softlayer)
    log("Initialize router: %s" % constellation_name)
# set ubuntu user and basic scripts on router
    _initialize_router(constellation_name, constellation_prefix,
                       partial_deploy,
                       credentials_softlayer,
                       constellation_directory)

    _initialize_private_machines(constellation_name,
                                 constellation_prefix,
                                 partial_deploy,
                                 ros_master_ip,
                                 credentials_softlayer,
                                 router_script,
                                 sim_script,
                                 fc1_script,
                                 fc2_script,
                                 constellation_directory)
# router, sim, fc1 and fc2 zip files
# edit /etc/network/interfaces and restart networking on all machines
    _change_ip_addresses(constellation_name,
                         partial_deploy,
                         credentials_softlayer,
                         constellation_directory)
# launch startup scripts
    _startup_scripts(constellation_name, partial_deploy)
    # disable access to sim fc1 and fc2 via their public ip addresses
    _shutdown_constellation_public_ips(constellation_name,
                                       constellation_prefix,
                                       partial_deploy,
                                       credentials_softlayer,
                                       constellation_directory)


def terminate_softlayer_constellation(constellation_name,
                       constellation_prefix,
                       partial_reload,
                       osrf_creds_fname):

    constellation = ConstellationState(constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= \
                             launch_sequence.index('os_reload'):
        return
    else:
        osrf_creds = load_osrf_creds(osrf_creds_fname)
        # compute the softlayer machine names
        constellation.set_value('sim_launch_msg', 'reload OS')
        machine_names = [x + "-" + constellation_prefix for x in ('router',
                                                                  'sim')]
        if not partial_reload:
            machine_names.append('fc2-' + constellation_prefix)
            machine_names.append('fc1-' + constellation_prefix)
            constellation.set_value('fc1_launch_msg', 'reload OS')
            constellation.set_value('fc2_launch_msg', 'reload OS')
        # enable nics on machines with disconnected ones (not the router)
        enable_public_ips(osrf_creds, machine_names[1:])
        for server in machine_names[1:]:
            t = get_active_transaction(osrf_creds, server)
            log("Transaction before reload on %s: %s" % (server, t))
        reload_servers(osrf_creds, machine_names)
        constellation.set_value("launch_stage", "os_reload")


def _change_ip_addresses(constellation_name,
                        partial_deploy,
                        credentials_softlayer,
                        constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'change_ip'):
        return
    m = "Setting private IP address"
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('router_launch_msg', m)

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    # change ip on sim
    ssh_router.cmd("cloudsim/set_sim_ip.bash")
    # change ip on router
    ssh_router.cmd("nohup sudo bash change_ip.bash %s"
        " > ssh_change_ip.out 2> ssh_change_ip.err < /dev/null &" % ROUTER_IP)

    if not partial_deploy:
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)
        ssh_router.cmd("cloudsim/set_fc1_ip.bash")
        ssh_router.cmd("cloudsim/set_fc2_ip.bash")

    constellation.set_value("launch_stage", "change_ip")


def _shutdown_constellation_public_ips(constellation_name,
                                      constellation_prefix,
                                      partial_deploy,
                                      credentials_softlayer,
                                      constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                    "block_public_ips"):
        return

    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "cloudsim/setup/done",
                       "running")

    m = "Switching off public network interfaces"
    constellation.set_value('sim_launch_msg', m)
    #constellation.set_value('router_launch_msg', m)
    private_machines = ["sim-%s" % constellation_prefix]
    if not partial_deploy:
        private_machines.append("fc1-%s" % constellation_prefix)
        private_machines.append("fc2-%s" % constellation_prefix)
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)

    osrf_creds = load_osrf_creds(credentials_softlayer)
    shutdown_public_ips(osrf_creds, private_machines)
    constellation.set_value("launch_stage", "block_public_ips")


def __add_ubuntu_user_to_router(router_ip, password,
                              constellation_directory,
                              key_prefix='key-router'):

    clean_local_ssh_key_entry(router_ip)
    create_ssh_key(key_prefix, constellation_directory)
    # setup a ubuntu sudoer no password user with an ssh key
    router_pub_key_path = os.path.join(constellation_directory,
                                       "%s.pem.pub" % key_prefix)
    setup_ssh_key_access(router_ip, password, router_pub_key_path)
    router_priv_key_path = os.path.join(constellation_directory,
                                        "%s.pem" % key_prefix)
    log("ssh -i %s ubuntu@%s" % (router_priv_key_path, router_ip))


def __upload_ssh_keys_to_router(ssh_router,
                              machine_prefix,
                              constellation_directory):
    # upload public key to router
    local_fname = os.path.join(constellation_directory,
                               'key-%s.pem.pub' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem.pub' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload public key %s to %s" % (local_fname, remote_fname))

    # upload private key to router
    local_fname = os.path.join(constellation_directory,
                               'key-%s.pem' % machine_prefix)
    remote_fname = 'cloudsim/key-%s.pem' % machine_prefix
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload private key %s to %s" % (local_fname, remote_fname))


def _wait_for_constellation_reload(constellation_name,
                                  constellation_prefix,
                                  partial_deploy,
                                  osrf_creds_fname):

    machines_dict = {}
    machines_dict['sim-%s' % constellation_prefix] = 'sim_launch_msg'
    machines_dict['router-%s' % constellation_prefix] = 'router_launch_msg'
    if not partial_deploy:
        machines_dict['fc2-%s' % constellation_prefix] = 'fc2_launch_msg'
        machines_dict['fc1-%s' % constellation_prefix] = 'fc1_launch_msg'

    log("machines_dict %s" % machines_dict)
    osrf_creds = load_osrf_creds(osrf_creds_fname)
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
    wait_for_server_reloads(osrf_creds, machines_dict.keys(),
                            reload_monitor.callback)


def _initialize_router(constellation_name,
                      constellation_prefix,
                      partial_deploy,
                      osrf_creds_fname,
                      constellation_directory):

    constellation = ConstellationState(constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index(
                                                                'init_router'):
        return

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    router_name = "router-%s" % constellation_prefix

    m = "running"
    constellation.set_value('fc1_aws_state', m)
    constellation.set_value('fc2_aws_state', m)
    constellation.set_value('sim_aws_state', m)
    constellation.set_value('router_aws_state', m)

    constellation.set_value('router_launch_msg', 'user account setup')
    router_ip, priv_ip, password = get_machine_login_info(osrf_creds,
                                                          router_name)
    constellation.set_value("router_public_ip", router_ip)
    log("router %s %s" % (router_ip, password))

    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(
                                osrf_creds, "sim-%s" % constellation_prefix)
    log("sim %s %s" % (sim_pub_ip, sim_root_password))

    log("ubuntu user setup for machine router %s [%s / %s] " % (router_name,
                                                                router_ip,
                                                                priv_ip))

    log("router %s %s : %s" % (router_name, router_ip, password))
    __add_ubuntu_user_to_router(router_ip, password, constellation_directory)

    softlayer_scripts_dir = os.path.join(
                    os.path.dirname(softlayer.__file__),
                    'bash')

    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)

    # create a remote cloudsim directory on the router
    ssh_router.cmd("mkdir -p cloudsim")

    openvpn_fname = os.path.join(constellation_directory, 'openvpn.key')
    create_openvpn_key(openvpn_fname)
    remote_fname = 'cloudsim/openvpn.key'
    ssh_router.upload_file(openvpn_fname, remote_fname)

    local_fname = os.path.join(softlayer_scripts_dir, 'router_init.bash')
    remote_fname = 'cloudsim/router_init.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    # upload ubuntu user setup scripts
    local_fname = os.path.join(softlayer_scripts_dir, 'auto_ubuntu.bash')
    remote_fname = 'cloudsim/auto_ubuntu.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir, 'create_ubuntu_user.exp')
    remote_fname = 'cloudsim/create_ubuntu_user.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir, 'upload_key.exp')
    remote_fname = 'cloudsim/upload_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    local_fname = os.path.join(softlayer_scripts_dir,
                               'process_remote_ssh_key.exp')
    remote_fname = 'cloudsim/process_remote_ssh_key.exp'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))
    # avoid ssh error because our server has changed
    constellation.set_value("launch_stage", "init_router")

    create_ssh_key("key-sim", constellation_directory)

    fc1_priv_ip = "0.0.0.0"
    fc2_priv_ip = "0.0.0.0"

    if not partial_deploy:
        fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(
                                osrf_creds, "fc1-%s" % constellation_prefix)
        log("fc1 %s %s" % (fc1_pub_ip, fc1_root_password))
        create_ssh_key("key-fc1", constellation_directory)

        fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(
                                osrf_creds, "fc2-%s" % constellation_prefix)
        log("fc2 %s %s" % (fc2_pub_ip, fc2_root_password))
        create_ssh_key("key-fc2", constellation_directory)

    arg_str = "%s %s %s" % (sim_priv_ip, fc1_priv_ip, fc2_priv_ip)
    cmd = "cd cloudsim; ./router_init.bash /home/ubuntu/cloudsim %s" % arg_str
    # run the script
    constellation.set_value('router_launch_msg', 'generating bash scripts')
    ssh_router.cmd(cmd)

    constellation.set_value('router_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "router", constellation_directory)
    constellation.set_value('sim_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "sim", constellation_directory)
    constellation.set_value('fc1_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "fc1", constellation_directory)
    constellation.set_value('fc2_launch_msg', 'uploading ssh key')
    __upload_ssh_keys_to_router(ssh_router, "fc2", constellation_directory)


def _provision_ssh_private_machine(constellation_name,
                                   ssh_router,
                                  machine_name_prefix,
                                  private_machine_ip,
                                  machine_password,
                                  startup_script,
                                  constellation_directory):

    constellation = ConstellationState(constellation_name)
    constellation.set_value('%s_launch_msg' % machine_name_prefix,
                                                'User account setup')

    # execute script on router to add ubuntu user on the private machine
    cmd = "cd cloudsim; ./auto_ubuntu.bash %s %s ./key-%s.pem.pub" % (
                private_machine_ip, machine_password, machine_name_prefix)
    log(cmd)
    ssh_router.cmd(cmd)

    local_fname = os.path.join(constellation_directory,
                               '%s_startup.bash' % machine_name_prefix)
    with open(local_fname, 'w') as f:
        f.write(startup_script)
    remote_fname = 'cloudsim/%s_startup_script.bash' % machine_name_prefix
    # send startup script to router
    ssh_router.upload_file(local_fname, remote_fname)


def _initialize_private_machines(constellation_name,
                                constellation_prefix,
                                partial_deploy,
                                credentials_softlayer,
                                router_script,
                                sim_script,
                                fc1_script,
                                fc2_script,
                                constellation_directory):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= \
                                    launch_sequence.index('init_privates'):
        return
    #
    # router machine
    #
    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory, "key-router", 'ubuntu',
                           router_ip)

    local_fname = os.path.join(constellation_directory, 'router_startup.bash')
    with open(local_fname, 'w') as f:
        f.write(router_script)
    remote_fname = 'cloudsim/router_startup_script.bash'
    ssh_router.upload_file(local_fname, remote_fname)
    log("upload %s to %s" % (local_fname, remote_fname))

    osrf_creds = load_osrf_creds(credentials_softlayer)
    #
    # sim machine
    #
    sim_pub_ip, sim_priv_ip, sim_root_password = get_machine_login_info(
                                osrf_creds, "sim-%s" % constellation_prefix)

    log("provision sim [%s / %s] %s" % (sim_pub_ip,
                                        sim_priv_ip, sim_root_password))
    _provision_ssh_private_machine(constellation_name,
                                   ssh_router,
                                   "sim",
                                   sim_priv_ip,
                                   sim_root_password,
                                   sim_script,
                                   constellation_directory)
    if not partial_deploy:
        #
        # fc1 machine
        #
        fc1_pub_ip, fc1_priv_ip, fc1_root_password = get_machine_login_info(
                                osrf_creds, "fc1-%s" % constellation_prefix)

        log("provision fc1 [%s / %s] %s" % (fc1_pub_ip, fc1_priv_ip,
                                            fc1_root_password))
        _provision_ssh_private_machine(constellation_name,
                                       ssh_router,
                                      "fc1",
                                      fc1_priv_ip,
                                      fc1_root_password,
                                      fc1_script,
                                      constellation_directory)
        #
        # fc2 machine
        #
        fc2_pub_ip, fc2_priv_ip, fc2_root_password = get_machine_login_info(
                                            osrf_creds,
                                            "fc2-%s" % constellation_prefix)

        log("provision fc2 [%s / %s] %s" % (fc2_pub_ip,
                                            fc2_priv_ip,
                                            fc2_root_password))

        _provision_ssh_private_machine(constellation_name,
                                       ssh_router,
                                       "fc2",
                                       fc2_priv_ip,
                                       fc2_root_password,
                                       fc2_script,
                                       constellation_directory)

    log('configure_machines done')
    constellation.set_value("launch_stage", "init_privates")


def _startup_scripts(constellation_name, partial_deploy):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    # if the change of ip was successful, the script should be in the home
    # directory of each machine
    __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       "change_ip.bash",
                       "packages_setup")

    m = "Executing startup script"
    constellation.set_value('sim_launch_msg', m)
    constellation.set_value('router_launch_msg', m)

    router_ip = constellation.get_value("router_public_ip")
    ssh_router = SshClient(constellation_directory,
                           "key-router",
                           'ubuntu',
                           router_ip)
    # load packages onto router
    ssh_router.cmd("nohup sudo bash cloudsim/router_startup_script.bash "
                   "> ssh_startup.out 2> ssh_startup.err < /dev/null &")
    # load packages onto simulator
    ssh_router.cmd("cloudsim/sim_init.bash")

    if not partial_deploy:
        constellation.set_value('fc1_launch_msg', m)
        constellation.set_value('fc2_launch_msg', m)
        # load packages onto fc1
        ssh_router.cmd("cloudsim/fc1_init.bash")
        # load packages onto fc2
        ssh_router.cmd("cloudsim/fc2_init.bash")
        constellation.set_value("fc1_state", "packages_setup")
        constellation.set_value("fc2_state", "packages_setup")

    constellation.set_value("sim_state", "packages_setup")
    constellation.set_value("router_state", "packages_setup")
    constellation.set_value("launch_stage", "startup")


def __wait_for_find_file(constellation_name,
                       constellation_directory,
                       partial_deploy,
                       ls_cmd,
                       end_state):

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
    #
    # Wait until machines are online (rebooted?)
    #
    q.append(get_ssh_cmd_generator(ssh_router,
                                        "ls %s" % ls_cmd,
                                        ls_cmd,
                                        constellation,
                                        "router_state",
                                        "running",
                                        max_retries=500))

    q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_sim.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "sim_state",
                                     end_state,
                                     max_retries=500))
    if not partial_deploy:
        q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_fc1.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "fc1_state",
                                     end_state,
                                     max_retries=500))

        q.append(get_ssh_cmd_generator(ssh_router,
                                     "cloudsim/find_file_fc2.bash %s" % ls_cmd,
                                     ls_cmd,
                                     constellation,
                                     "fc2_state",
                                     end_state,
                                     max_retries=500))

    empty_ssh_queue(q, sleep=2)
