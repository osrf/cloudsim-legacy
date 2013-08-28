from __future__ import print_function

import unittest
import os
import time
import commands

import tempfile
import shutil


from launch_utils import get_unique_short_name


from launch_utils import SshClient
from launch_utils import ConstellationState  # launch_db
from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_cloudsim_startup_script
from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.monitoring import constellation_is_terminated
from launch_utils.monitoring import monitor_cloudsim_ping
from launch_utils.monitoring import monitor_launch_state

from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue
from launch_utils.launch_db import get_cloudsim_config, log_msg, set_cloudsim_config


from vrc_contest import create_private_machine_zip
from launch_utils import acquire_aws_server, terminate_aws_server
from launch_utils.openstack import acquire_openstack_server, terminate_openstack_server, get_nova_creds
from launch_utils.sl_cloud import acquire_dedicated_sl_server,\
    terminate_dedicated_sl_server


CONFIGURATION = "cloudsim"
CLOUDSIM_ZIP_PATH = '/var/www-cloudsim-auth/cloudsim.zip'


def log(msg, channel=__name__, severity='info'):
    log_msg(msg, channel, severity)


def update(constellation_name):
    """
    Update the constellation software on the servers.
    This function is a plugin function that should be implemented by
    each constellation type
    """
    log("Cloudsim update of constellation %s " % constellation_name)
    key_prefix = _extract_key_prefix(constellation_name)
    # Do the software update here, via ssh
    website_distribution = CLOUDSIM_ZIP_PATH
    upload_and_deploy_cloudsim(constellation_name, website_distribution,
                               key_prefix,
                               force=False)
    constellation = ConstellationState(constellation_name)
    constellation.set_value('simulation_launch_msg', "running")


def start_task(constellation_name, package_name, launch_file_name,
               timeout, launch_args, latency, data_cap):

    for _ in range(10):
        log("*****")
    log("start_task constellation %s, package_name %s, launch_file_name %s,"
        " timeout %s, launch_args %s, latency %s, data_cap %s" %
        (constellation_name, package_name, launch_file_name, timeout, launch_args,
         latency, data_cap))


def get_softlayer_path():
    config = get_cloudsim_config()
    osrf_creds_fname = config['softlayer_path']
    return osrf_creds_fname


def stop_task(constellation):
    log("** STOP TASK %s ***" % constellation)


def _extract_key_prefix(constellation_name):
    key_prefix = None
    if not "OSRF" in constellation_name:
        key_prefix = "key-cs-%s" % constellation_name
    else:
        key_prefix = "key-cs"
    return key_prefix


def monitor(constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True

    _extract_key_prefix(constellation_name)
    constellation = ConstellationState(constellation_name)

    if constellation.has_value("simulation_ip"):
        key_prefix = _extract_key_prefix(constellation_name)
        ip = constellation.get_value("simulation_ip")
        simulation_state = constellation.get_value('simulation_state')
        constellation_directory = constellation.get_value(
                                                    "constellation_directory")
        ssh_sim = SshClient(constellation_directory, key_prefix, 'ubuntu', ip)
        monitor_cloudsim_ping(constellation_name,
                              'simulation_ip',
                              'simulation_latency')
        monitor_launch_state(constellation_name,
                 ssh_sim,
                 simulation_state,
                 "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg')
    return False

launch_sequence = ["nothing", "os_reload", "init", "zip",  "change_ip",
                   "startup", "reboot", "running"]


def create_zip(constellation_name, key_prefix):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value(
                                                    "constellation_directory")
    fname_zip = os.path.join(constellation_directory,
                             "cs", "%s_%s.zip" % ("cs", constellation_name))

    launch_stage = constellation.get_value("launch_stage")

    if launch_sequence.index(launch_stage) >= launch_sequence.index('zip'):
        return fname_zip

    log("constellation name %s" % constellation_name)
    constellation = ConstellationState(constellation_name)
    log("%s" % constellation.get_values())
    ip = constellation.get_value("simulation_ip")

    constellation_directory = constellation.get_value(
                                                    "constellation_directory")
    create_private_machine_zip("cs",
                                 ip,
                                 constellation_name,
                                 constellation_directory,
                                 key_prefix)
    constellation.set_value('sim_zip_file', 'ready')
    constellation.set_value("launch_stage", "zip")
    return fname_zip


def startup_script(constellation_name):
    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')

    ip = constellation.get_value("simulation_ip")
    ssh_client = SshClient(constellation_directory, "key-cs", 'ubuntu', ip)

    local_fname = os.path.join(constellation_directory, 'cs_startup.bash')
    script = get_cloudsim_startup_script()
    with open(local_fname, 'w') as f:
        f.write(script)

    remote_fname = "startup_script.bash"
    ssh_client.upload_file(local_fname, remote_fname)
    # load packages onto router
    ssh_client.cmd("nohup sudo bash startup_script.bash"
                   " > ssh_startup.out 2> ssh_startup.err < /dev/null &")
    # load packages onto fc1

    constellation.set_value("launch_stage", "startup")


def upload_and_deploy_cloudsim(constellation_name,
                               website_distribution,
                               key_prefix,
                               force=False):

    constellation_state = ConstellationState(constellation_name)
    constellation_dir = constellation_state.get_value(
                                                    'constellation_directory')
    ip_address = constellation_state.get_value("simulation_ip")
    ssh_cli = SshClient(constellation_dir, key_prefix, 'ubuntu', ip_address)
    short_file_name = os.path.split(website_distribution)[1]
    remote_filename = "/home/ubuntu/%s" % (short_file_name)
    log("uploading '%s' to the server to '%s'" % (website_distribution,
                                                  remote_filename))

    constellation_state.set_value('simulation_launch_msg',
                                  "uploading CloudSim distribution")
    out_s = ssh_cli.upload_file(website_distribution, remote_filename)
    log(" upload: %s" % out_s)

    constellation_state.set_value('simulation_launch_msg', "unzip web app")
    log("unzip web app")
    out_s = ssh_cli.cmd("unzip -o " + remote_filename)
    log("\t%s" % out_s)
    constellation_state.set_value('simulation_launch_msg', "deploying web app")

    if force:
        ssh_cli.cmd('cp cloudsim_users cloudsim/distfiles/users')

    log("Deploying the cloudsim web app")
    deploy_script_fname = "/home/ubuntu/cloudsim/deploy.sh"
    # If asked, pass -f to force deploy.sh to overwrite any existing users file
    if force:
        deploy_script_fname += " -f"
    log("running deploy script '%s' remotely" % deploy_script_fname)
    out_s = ssh_cli.cmd("bash " + deploy_script_fname)
    log("\t%s" % out_s)


def launch(username, configuration, constellation_name, tags,
           constellation_directory, website_distribution=CLOUDSIM_ZIP_PATH):

    machine_prefix = "cs"
    cfg = get_cloudsim_config()

    log('launch!!! tags = %s' % tags)
    cloud_provider = tags['cloud_provider']
    constellation = ConstellationState(constellation_name)
    constellation.set_value("cloud_provider", cloud_provider)
    constellation.set_value("simulation_launch_msg", "launching")
    constellation.set_value('simulation_state', 'starting')
    constellation.set_value("launch_stage", "nothing")
    constellation.set_value('simulation_latency', '[]')

    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('simulation_state', 'network_setup')
    constellation.set_value('simulation_aws_state', 'pending')
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('simulation_latency', '[]')
    constellation.set_value('sim_zip_file', 'not ready')
    constellation.set_value("error", "")

    constellation.set_value("gazebo", "not running")
    constellation.set_value('sim_glx_state', "not running")

    auto_launch_configuration = None
    jr_softlayer_path = cfg['softlayer_path']
    jr_cloudsim_portal_key_path = cfg['cloudsim_portal_key_path']
    jr_cloudsim_portal_json_path = cfg['cloudsim_portal_json_path']
    jr_bitbucket_key_path = cfg['cloudsim_bitbucket_key_path']
    jr_other_users = cfg['other_users']
    jr_cs_role = cfg['cs_role']
    jr_cs_admin_users = cfg['cs_admin_users']

    if 'args' in tags:
        if type(tags['args']) == type(str()):
            # Backward compatibility: if args is a string,
            # it's the configuration to launch
            auto_launch_configuration = tags['args']

        elif type(tags['args']) == type(dict()):
            # Otherwise, it should be a dictionary
            d = tags['args']
            auto_launch_configuration = d['auto_launch_configuration']
            # And we pull junior's credential file paths from the provided
            # dictionary
            jr_softlayer_path = d['softlayer_path']
            jr_cloudsim_portal_key_path = d['cloudsim_portal_key_path']
            jr_cloudsim_portal_json_path = d['cloudsim_portal_json_path']
            jr_bitbucket_key_path = d['cloudsim_bitbucket_key_path']
            jr_other_users = d['other_users']
            jr_cs_role = d['cs_role']
            jr_cs_admin_users = d['cs_admin_users']
        else:
            log('Error: tags[\'args\'] is neither a string'
                ' nor a dictionary: %s' % (str(tags['args'])))

    log('auto_launch_configuration %s' % auto_launch_configuration)

    constellation.set_value("simulation_launch_msg",
                            "setting up user accounts and keys")

    pub_ip = None
    key_prefix = None
    if "Amazon" in  cloud_provider:
        aws_creds_fname = cfg['boto_path']
        script = get_cloudsim_startup_script()
        pub_ip, aws_id, key_prefix = acquire_aws_server(constellation_name,
                                    aws_creds_fname,
                                    constellation_directory,
                                    machine_prefix,
                                    script,
                                    tags)
        # (constellation_name, credentials_ec2, constellation_directory, tags)
        constellation.set_value("aws_id", aws_id)
    elif "OpenStack" in cloud_provider:
        openstack_creds = get_nova_creds()
        script = get_cloudsim_startup_script()
        pub_ip, instance_id, key_prefix = acquire_openstack_server(
                                    constellation_name,
                                    openstack_creds,
                                    constellation_directory,
                                    machine_prefix,
                                    script)
        log("KEY PREFIX---------%s" % key_prefix)
        log("IP ADDR---------%s" % pub_ip)
        constellation.set_value("aws_id", instance_id)
        #ip address, instance id, key prefix (no .pem)
    elif "SoftLayer" in cloud_provider:
        osrf_creds_fname = cfg['softlayer_path']
        pub_ip, _, _ = acquire_dedicated_sl_server(constellation_name,
                           osrf_creds_fname,
                           constellation_directory)
        key_prefix = "key-cs"
        constellation.set_value('simulation_state', 'packages_setup')
        constellation.set_value("simulation_launch_msg", "install packages")
        startup_script(constellation_name)
    else:
        raise Exception("Unsupported cloud provider: %s" % (cloud_provider))
    log("SIMULATION IP ---- %s" % pub_ip)
    constellation.set_value("simulation_ip", pub_ip)
    log("%s" % constellation.get_value("simulation_ip"))

    constellation.set_value("simulation_launch_msg", "create zip file")
    log("create zip")
    fname_zip = create_zip(constellation_name, key_prefix)

    #create a copy for downloads
    local_zip = os.path.join(constellation_directory, "CloudSim.zip")
    shutil.copy(fname_zip, local_zip)

    log("install packages")

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")

    ip = constellation.get_value("simulation_ip")
    clean_local_ssh_key_entry(ip)

    constellation.set_value('simulation_ip', ip)
    log("%s simulation machine ip %s" % (constellation_name, ip))
    ssh_sim = SshClient(constellation_directory, key_prefix, 'ubuntu', ip)

    constellation.set_value('simulation_launch_msg', "waiting for network")
    networking_done = get_ssh_cmd_generator(ssh_sim,
                                            "ls launch_stdout_stderr.log",
                                            "launch_stdout_stderr.log",
                                            constellation,
                                            "simulation_state",
                                            'packages_setup',
                                            max_retries=100)
    empty_ssh_queue([networking_done], sleep=2)
    ssh_sim.cmd("mkdir -p cloudsim")
    constellation.set_value('simulation_launch_msg',
                            "creating monitoring scripts")
    find_file_sim = """
    #!/bin/bash

    ls \$1

    """
    ssh_sim.create_file(find_file_sim, "cloudsim/find_file_sim.bash")

    dpkg_log_sim = """
    #!/bin/bash

    tail -1 /var/log/dpkg.log

    """
    ssh_sim.create_file(dpkg_log_sim, "cloudsim/dpkg_log_sim.bash")

    constellation.set_value('simulation_launch_msg',
                            "waiting for packages to install")
    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done",
                                           "cloudsim/setup/done",
                                           constellation,
                                           "simulation_state",
                                           'packages_setup',
                                           max_retries=100)
    empty_ssh_queue([sim_setup_done], sleep=2)

    log("Setup admin user %s" % username)

    # Sourround with double quotes all the users
    jr_cs_admin_users = ['"' + user + '"' for user in jr_cs_admin_users]
    users = ['"' + username + '"'] + ['"' + user + '"' for user in
                                      jr_other_users]

    add_user_cmd = 'echo \'{'

    # Team user list
    add_user_cmd += (':"' + jr_cs_role + '",').join(users)
    add_user_cmd += ':"' + jr_cs_role + '"'

    # Additional admin users
    if jr_cs_admin_users:
        add_user_cmd += ','
        add_user_cmd += ':"admin",'.join(jr_cs_admin_users)
        add_user_cmd += ':"admin"'

    add_user_cmd += '}\' > cloudsim_users'

    log("add users to cloudsim: %s" % add_user_cmd)
    out = ssh_sim.cmd(add_user_cmd)
    log("\t%s" % out)

    # fname_zip = os.path.join(constellation_directory, "cs","cs.zip")
    log("Uploading the key file to the server")
    constellation.set_value('simulation_launch_msg',
                            "Uploading the key file to the server")
    remote_fname = "/home/ubuntu/cloudsim/cloudsim_ssh.zip"
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname))
    out = ssh_sim.upload_file(fname_zip, remote_fname)
    log("\t%s" % out)

    if jr_softlayer_path is not None and os.path.exists(jr_softlayer_path):
        constellation.set_value('simulation_launch_msg',
                        "Uploading the SoftLayer credentials to the server")
        remote_fname = "/home/ubuntu/softlayer.json"
        log("uploading '%s' to the server to '%s'" % (jr_softlayer_path,
                                                      remote_fname))
        out = ssh_sim.upload_file(jr_softlayer_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value('simulation_launch_msg',
                                "No SoftLayer credentials loaded")

    ec2_creds_fname = cfg['boto_path']
    if ec2_creds_fname is not None and os.path.exists(ec2_creds_fname):
        # todo ... set the name, upload both files
        constellation.set_value('simulation_launch_msg',
                                "Uploading the ec2 credentials to the server")
        remote_fname = "/home/ubuntu/boto.ini"
        log("uploading '%s' to the server to '%s'" % (ec2_creds_fname,
                                                      remote_fname))
        out = ssh_sim.upload_file(ec2_creds_fname, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value('simulation_launch_msg',
                                "No Amazon Web Services credentials loaded")

    if jr_cloudsim_portal_key_path is not None and \
            os.path.exists(jr_cloudsim_portal_key_path) and \
            jr_cloudsim_portal_json_path is not None and \
            os.path.exists(jr_cloudsim_portal_json_path):
        constellation.set_value('simulation_launch_msg',
                                "Uploading the Portal key to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.key"
        log("uploading '%s' to the server to '%s'" % (
                                    jr_cloudsim_portal_key_path, remote_fname))
        out = ssh_sim.upload_file(jr_cloudsim_portal_key_path, remote_fname)
        log("\t%s" % out)

        constellation.set_value('simulation_launch_msg',
                                "Uploading the Portal JSON file to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.json"
        log("uploading '%s' to the server to '%s'" % (
                                jr_cloudsim_portal_json_path, remote_fname))
        out = ssh_sim.upload_file(jr_cloudsim_portal_json_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value('simulation_launch_msg',
                                "No portal key or json file found")

    if jr_bitbucket_key_path is not None and \
                        os.path.exists(jr_bitbucket_key_path):
        constellation.set_value('simulation_launch_msg',
                                "Uploading the bitbucket key to the server")
        remote_fname = "/home/ubuntu/cloudsim_bitbucket.key"
        log("uploading '%s' to the server to '%s'" % (jr_bitbucket_key_path,
                                                                remote_fname))
        out = ssh_sim.upload_file(jr_bitbucket_key_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value('simulation_launch_msg',
                                "No bitbucket key uploaded")
    #
    #  Upload cloudsim.zip and Deploy
    #
    upload_and_deploy_cloudsim(constellation_name,
                               website_distribution,
                               key_prefix,
                               force=True)
    #
    # For a CLoudSim launch, we look at the tags for a configuration to launch
    # at the end.
    if auto_launch_configuration:

        msg = ("Launching a constellation"
               " of type \"%s\"" % auto_launch_configuration)
        log(msg)
        constellation.set_value('simulation_launch_msg', msg)
        time.sleep(20)
        ssh_sim.cmd("/home/ubuntu/cloudsim/launch.py"
                    " \"%s\" \"%s\"" % (username, auto_launch_configuration))

    print ("\033[1;32mCloudSim ready. Visit http://%s \033[0m\n" % ip)
    print ("Stop your CloudSim using the AWS console")
    print ("     http://aws.amazon.com/console/\n")

    constellation.set_value('simulation_state', 'running')
    constellation.set_value('constellation_state', 'running')
    time.sleep(10)
    constellation.set_value('simulation_launch_msg', "Complete")
    log("provisioning done")


def terminate(constellation_name):

    constellation = ConstellationState(constellation_name)
    constellation.set_value('simulation_launch_msg', "terminating")
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('simulation_state', 'terminating')

    log("terminate %s [constellation_name=%s]" % (CONFIGURATION,
                                                  constellation_name))

    cs_cfg = get_cloudsim_config()
    softlayer_path = cs_cfg['softlayer_path']

    constellation.set_value("launch_stage", "nothing")

    cloud_provider = constellation.get_value("cloud_provider")
    if "Amazon" in  cloud_provider:
        terminate_aws_server(constellation_name)
    elif "OpenStack" in cloud_provider:
        terminate_openstack_server(constellation_name)
    elif "SoftLayer" in cloud_provider:
        constellation_prefix = constellation_name.split("OSRF_CloudSim_")[1]
        machine_name = "cs-%s" % constellation_prefix
        terminate_dedicated_sl_server(constellation_name,
                                      machine_name,
                                      softlayer_path)

    constellation.set_value('simulation_aws_state', 'terminated')
    constellation.set_value('simulation_state', "terminated")
    constellation.set_value('simulation_launch_msg', "terminated")
    constellation.set_value('constellation_state', 'terminated')


def cloudsim_bootstrap(username, credentials_ec2,
                       initial_constellation, config):

    set_cloudsim_config(config)

    constellation_name = get_unique_short_name('c')

    gmt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    tags = {'GMT': gmt,
            'username': username,
            }

    constellation_directory = tempfile.mkdtemp("cloudsim")
    website_distribution = zip_cloudsim()

    constellation = ConstellationState(constellation_name)
    constellation.set_value('username', username)
    constellation.set_value('constellation_name', constellation_name)
    constellation.set_value('gmt', gmt)
    constellation.set_value('configuration', 'cloudsim')
    constellation.set_value('constellation_directory', constellation_directory)
    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('error', '')

    return launch(username, 'CloudSim', constellation_name, tags,
                  constellation_directory, website_distribution)


def zip_cloudsim():

    tmp_dir = tempfile.mkdtemp("cloudsim")
    tmp_zip = os.path.join(tmp_dir, "cloudsim.zip")
    p = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    full_path_of_cloudsim = os.path.dirname(p)
    # Account for having a version in the name of the directory, which we
    # want to get rid of
    shutil.copytree(full_path_of_cloudsim, os.path.join(tmp_dir, 'cloudsim'))
    os.chdir(tmp_dir)
    commands.getoutput('zip -r %s cloudsim' % (tmp_zip))

    return tmp_zip


class JustInCase(unittest.TestCase):

    def test_launch(self):

        launch_stage = None  # use the current stage
        # "nothing", "os_reload", "init_router", "init_privates",
        # "zip",  "change_ip", "startup", "reboot", "running"
        self.tags = {}

        self.constellation_name = 'OSRF CloudSim 01'
        self.username = "toto@osrfoundation.org"
        CONFIGURATION = 'cloudsim'
        self.tags.update({'TestCase': CONFIGURATION,
                          'configuration': 'cloudsim',
                          'constellation': self.constellation_name,
                          'user': self.username,
                          'GMT': "now"})

        self.credentials_softlayer = get_softlayer_path()

        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name = get_unique_short_name(test_name + "_")
            self.constellation_directory = os.path.abspath(
                                        os.path.join(get_test_path(test_name),
                                        self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            self.constellation_directory = os.path.abspath(
             os.path.join(get_test_path(test_name), self.constellation_name))

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory",
                                self.constellation_directory)
        constellation.set_value("configuration", 'cloudsim')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)

        launch(self.username,
               "CloudSim",
               self.constellation_name,
               self.tags,
               self.credentials_softlayer,
               self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.username,
                    self.constellation_name,
                    self.credentials_softlayer,
                    i)

            time.sleep(1)

        terminate(self.constellation_name,
                  self.credentials_softlayer,
                  self.constellation_directory)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
