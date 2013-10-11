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
from launch_utils.testing import get_test_runner, get_test_path, get_boto_path
from launch_utils.monitoring import constellation_is_terminated
from launch_utils.monitoring import monitor_cloudsim_ping
from launch_utils.monitoring import monitor_launch_state

from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue
from launch_utils.launch_db import get_cloudsim_config, log_msg
from launch_utils.launch_db import set_cloudsim_config

from vrc_contest import create_private_machine_zip
from launch_utils import terminate_aws_server

from launch_utils.openstack import acquire_openstack_server
from launch_utils.openstack import terminate_openstack_server
from launch_utils.openstack import get_nova_creds

from launch_utils.sl_cloud import acquire_dedicated_sl_server,\
    terminate_dedicated_sl_server
import json
from launch_utils.aws import acquire_aws_single_server


CONFIGURATION = "cloudsim"
CLOUDSIM_ZIP_PATH = '/var/www-cloudsim-auth/cloudsim.zip'

LAUNCH_MSG_KEY = "cs_launch_msg"
STATE_KEY = 'cs_state'
IP_KEY = "cs_public_ip"
LATENCY_KEY = 'cs_latency'
ZIP_READY_KEY = 'cs_zip_file'


def log(msg, channel=__name__, severity='info'):
    log_msg(msg, channel, severity)


def update(constellation_name):
    """
    Update the constellation software on the servers.
    This function is a plugin function that should be implemented by
    each constellation type
    """
    log("Cloudsim update of constellation %s " % constellation_name)
    constellation = ConstellationState(constellation_name)

    for machine in ["simulation"]:
        constellation.set_value("%s_state" % machine, "packages_setup")
        constellation.set_value("%s_launch_msg" % machine, "updating software")

    key_prefix = _extract_key_prefix(constellation_name)
    # Do the software update here, via ssh
    website_distribution = CLOUDSIM_ZIP_PATH
    upload_cloudsim(constellation_name, website_distribution,
                               key_prefix)
    constellation_dir = constellation.get_value('constellation_directory')
    ip_address = constellation.get_value(IP_KEY)
    ssh_cli = SshClient(constellation_dir, key_prefix, 'ubuntu', ip_address)

    # Upload the installed apache2.conf from the papa cloudsim so that the
    # junior cloudsim is configured the same way (e.g., uses basic auth instead
    # of openid).
    ssh_cli.upload_file('/etc/apache2/apache2.conf',
                        'cloudsim/distfiles/apache2.conf')

    log("Deploying the cloudsim web app")
    deploy_script_fname = "/home/ubuntu/cloudsim/deploy.sh"
    out_s = ssh_cli.cmd("bash " + deploy_script_fname)
    log("\t%s" % out_s)
    constellation = ConstellationState(constellation_name)

    for machine in ["simulation"]:
        constellation.set_value("%s_state" % machine, "running")

    time.sleep(10)
    constellation.set_value(LAUNCH_MSG_KEY, "complete")


def start_task(constellation_name, package_name, launch_file_name,
               timeout, launch_args, latency, data_cap):

    for _ in range(10):
        log("*****")
    log("start_task constellation %s, package_name %s, launch_file_name %s,"
        " timeout %s, launch_args %s, latency %s, data_cap %s" %
        (constellation_name, package_name, launch_file_name, timeout,
         launch_args, latency, data_cap))


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

    if constellation.has_value(IP_KEY):
        ip = constellation.get_value(IP_KEY)
        simulation_state = constellation.get_value(STATE_KEY)
        constellation_directory = constellation.get_value(
                                                    "constellation_directory")
        ssh_sim = SshClient(constellation_directory, "key-cs", 'ubuntu', ip)
        monitor_cloudsim_ping(constellation_name,
                              IP_KEY,
                              LATENCY_KEY)
        monitor_launch_state(constellation_name,
                 ssh_sim,
                 simulation_state,
                 "bash cloudsim/dpkg_log_sim.bash", LAUNCH_MSG_KEY)
    return False

launch_sequence = ["nothing", "os_reload", "init", "zip",  "change_ip",
                   "startup", "reboot", "running"]


def create_zip(constellation_name, key_prefix, ip):
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
    constellation_directory = constellation.get_value(
                                                    "constellation_directory")
    create_private_machine_zip("cs",
                               ip,
                               constellation_name,
                               constellation_directory,
                               key_prefix)
    constellation.set_value(ZIP_READY_KEY, 'ready')
    constellation.set_value("launch_stage", "zip")
    return fname_zip


def startup_script(constellation_name):
    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')

    ip = constellation.get_value(IP_KEY)
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


def upload_cloudsim(constellation_name,
                               website_distribution,
                               key_prefix):

    constellation = ConstellationState(constellation_name)
    constellation_dir = constellation.get_value(
                                                    'constellation_directory')
    ip_address = constellation.get_value(IP_KEY)
    ssh_cli = SshClient(constellation_dir, key_prefix, 'ubuntu', ip_address)
    short_file_name = os.path.split(website_distribution)[1]
    remote_filename = "/home/ubuntu/%s" % (short_file_name)
    log("uploading '%s' to the server to '%s'" % (website_distribution,
                                                  remote_filename))

    constellation.set_value(LAUNCH_MSG_KEY,
                                  "uploading CloudSim distribution")
    out_s = ssh_cli.upload_file(website_distribution, remote_filename)
    log(" upload: %s" % out_s)

    constellation.set_value(LAUNCH_MSG_KEY, "unzip web app")
    log("unzip web app")
    out_s = ssh_cli.cmd("unzip -o " + remote_filename)
    log("\t%s" % out_s)
    constellation.set_value(LAUNCH_MSG_KEY, "deploying web app")


def launch(constellation_name, tags, website_distribution=CLOUDSIM_ZIP_PATH):

    constellation = ConstellationState(constellation_name)
    cloudsim_stable = True
    if constellation.get_value('configuration') == 'CloudSim':
        cloudsim_stable = False

    script = None
    image_key = None

    if not cloudsim_stable:
        script = script = get_cloudsim_startup_script()
        image_key = 'ubuntu_1204_x64'
    else:
        script = ''
        image_key = 'ubuntu_1204_x64_cloudsim_stable'

    log("cloudsim launch %s  %s zip = %s" % (constellation_name,
                                             tags, website_distribution))
    cloud_provider = tags['cloud_provider']
    username = tags['username']
    #constellation_name = tags['constellation_name']
    constellation_directory = tags['constellation_directory']
    credentials_fname = os.path.join(constellation_directory,
                                     'credentials.txt')

    machine_prefix = "cs"
    cfg = get_cloudsim_config()

    log('launch!!! tags = %s' % tags)

    constellation.set_value(LAUNCH_MSG_KEY, "launching")
    constellation.set_value(STATE_KEY, 'starting')
    constellation.set_value("launch_stage", "nothing")
    constellation.set_value(LATENCY_KEY, '[]')

    constellation.set_value('constellation_state', 'launching')
    constellation.set_value(STATE_KEY, 'network_setup')

    constellation.set_value(LAUNCH_MSG_KEY, "starting")
    constellation.set_value(LATENCY_KEY, '[]')
    constellation.set_value(ZIP_READY_KEY, 'not ready')
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

    constellation.set_value(LAUNCH_MSG_KEY,
                            "setting up user accounts and keys")

    pub_ip = None
    key_prefix = "key-cs"
    if cloud_provider == "aws":
        machine = {'hardware': 'm1.small',
                      'ip': "127.0.0.1",
                      'software': image_key,
                      'security_group': [{'name': 'ping',
                                           'protocol': 'icmp',
                                          'from_port': -1,
                                          'to_port': -1,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'ssh',
                                           'protocol': 'tcp',
                                          'from_port': 22,
                                          'to_port': 22,
                                          'cidr': '0.0.0.0/0', },
                                          {'name': 'http',
                                          'protocol': 'tcp',
                                          'from_port': 80,
                                          'to_port':80,
                                          'cidr': '0.0.0.0/0', }, ]
                        }

        pub_ip, _, _ = acquire_aws_single_server(constellation_name,
                              credentials_ec2=credentials_fname,
                              constellation_directory=constellation_directory,
                              machine_prefix="cs",
                              machine_data=machine,
                              startup_script=script,
                              tags=tags)

    elif "OpenStack" in cloud_provider:
        openstack_creds = cfg['openstack']
        pub_ip, _, key_prefix = acquire_openstack_server(
                                    constellation_name,
                                    openstack_creds,
                                    constellation_directory,
                                    machine_prefix,
                                    script)
        log("KEY PREFIX---------%s" % key_prefix)
        log("IP ADDR---------%s" % pub_ip)

    elif cloud_provider == "softlayer":
        pub_ip, _, _ = acquire_dedicated_sl_server(constellation_name,
                           credentials_fname,
                           constellation_directory)

        constellation.set_value(STATE_KEY, 'packages_setup')
        constellation.set_value(LAUNCH_MSG_KEY, "install packages")
        startup_script(constellation_name)
    else:
        raise Exception("Unsupported cloud provider: %s" % (cloud_provider))

    log("SIMULATION IP ---- %s" % pub_ip)
    constellation.set_value(IP_KEY, pub_ip)
    log("%s" % constellation.get_value(IP_KEY))

    constellation.set_value(LAUNCH_MSG_KEY, "create zip file")
    log("create zip")
    fname_zip = create_zip(constellation_name, key_prefix, pub_ip)

    #create a copy for downloads
    local_zip = os.path.join(constellation_directory, "CloudSim.zip")
    shutil.copy(fname_zip, local_zip)

    ip = constellation.get_value(IP_KEY)
    clean_local_ssh_key_entry(ip)

    log("install packages")

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")

    constellation.set_value(IP_KEY, ip)
    log("%s simulation machine ip %s" % (constellation_name, ip))
    ssh_cli = SshClient(constellation_directory, key_prefix, 'ubuntu', ip)

    constellation.set_value(LAUNCH_MSG_KEY, "waiting for network")

    sim_setup_done = get_ssh_cmd_generator(ssh_cli, "ls cloudsim/setup/done",
                                           "cloudsim/setup/done",
                                           constellation,
                                           STATE_KEY,
                                           'packages_setup',
                                           max_retries=100)
    empty_ssh_queue([sim_setup_done], sleep=2)

    log("Setup admin user %s and friends" % username)
    users = {"guest": "officer", username: "admin", "user": "user"}
    for u in jr_cs_admin_users:
        users[u] = "admin"
    for u in jr_other_users:
        users[u] = jr_cs_role

    fname_users = os.path.join(constellation_directory, "cloudsim_users")
    with open(fname_users, 'w') as f:
        s = json.dumps(users)
        f.write(s)

    remote_fname = "/home/ubuntu/cloudsim_users"
    log("uploading '%s' to the server to '%s'" % (fname_users, remote_fname))
    out = ssh_cli.upload_file(fname_users, remote_fname)
    log("\t%s" % out)

    # Add the currently logged-in user to the htpasswd file on the cloudsim
    # junior.  This file will be copied into the installation location later in
    # upload_cloudsim().
    htpasswd_cmd = 'htpasswd -bc cloudsim_htpasswd %s admin%s' % (username,
                                                            constellation_name)
    log("add current user to htpasswd file: %s" % htpasswd_cmd)
    out = ssh_cli.cmd(htpasswd_cmd)
    log("\t%s" % out)

    htpasswd_cmd = 'htpasswd -b cloudsim_htpasswd guest %s' % (
                                                            constellation_name)
    log("add officer user to htpasswd file: %s" % htpasswd_cmd)
    out = ssh_cli.cmd(htpasswd_cmd)
    log("\t%s" % out)

    htpasswd_cmd = 'htpasswd -b cloudsim_htpasswd user %s' % (
                                                            constellation_name)

    log("add user to htpasswd file: %s" % htpasswd_cmd)
    out = ssh_cli.cmd(htpasswd_cmd)
    log("\t%s" % out)

    # fname_zip = os.path.join(constellation_directory, "cs","cs.zip")
    log("Uploading the key file to the server")
    constellation.set_value(LAUNCH_MSG_KEY,
                            "Uploading the key file to the server")
    remote_fname = "/home/ubuntu/cloudsim/cloudsim_ssh.zip"
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname))
    out = ssh_cli.upload_file(fname_zip, remote_fname)
    log("\t%s" % out)

    if jr_softlayer_path is not None and os.path.exists(jr_softlayer_path):
        constellation.set_value(LAUNCH_MSG_KEY,
                        "Uploading the SoftLayer credentials to the server")
        remote_fname = "/home/ubuntu/softlayer.json"
        log("uploading '%s' to the server to '%s'" % (jr_softlayer_path,
                                                      remote_fname))
        out = ssh_cli.upload_file(jr_softlayer_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value(LAUNCH_MSG_KEY,
                                "No SoftLayer credentials loaded")

    ec2_creds_fname = cfg['boto_path']
    if ec2_creds_fname is not None and os.path.exists(ec2_creds_fname):
        # todo ... set the name, upload both files
        constellation.set_value(LAUNCH_MSG_KEY,
                                "Uploading the ec2 credentials to the server")
        remote_fname = "/home/ubuntu/boto.ini"
        log("uploading '%s' to the server to '%s'" % (ec2_creds_fname,
                                                      remote_fname))
        out = ssh_cli.upload_file(ec2_creds_fname, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value(LAUNCH_MSG_KEY,
                                "No Amazon Web Services credentials loaded")

    if jr_cloudsim_portal_key_path is not None and \
            os.path.exists(jr_cloudsim_portal_key_path) and \
            jr_cloudsim_portal_json_path is not None and \
            os.path.exists(jr_cloudsim_portal_json_path):
        constellation.set_value(LAUNCH_MSG_KEY,
                                "Uploading the Portal key to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.key"
        log("uploading '%s' to the server to '%s'" % (
                                    jr_cloudsim_portal_key_path, remote_fname))
        out = ssh_cli.upload_file(jr_cloudsim_portal_key_path, remote_fname)
        log("\t%s" % out)

        constellation.set_value(LAUNCH_MSG_KEY,
                                "Uploading the Portal JSON file to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.json"
        log("uploading '%s' to the server to '%s'" % (
                                jr_cloudsim_portal_json_path, remote_fname))
        out = ssh_cli.upload_file(jr_cloudsim_portal_json_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value(LAUNCH_MSG_KEY,
                                "No portal key or json file found")

    if jr_bitbucket_key_path is not None and \
                        os.path.exists(jr_bitbucket_key_path):
        constellation.set_value(LAUNCH_MSG_KEY,
                                "Uploading the bitbucket key to the server")
        remote_fname = "/home/ubuntu/cloudsim_bitbucket.key"
        log("uploading '%s' to the server to '%s'" % (jr_bitbucket_key_path,
                                                                remote_fname))
        out = ssh_cli.upload_file(jr_bitbucket_key_path, remote_fname)
        log("\t%s" % out)
    else:
        constellation.set_value(LAUNCH_MSG_KEY,
                                "No bitbucket key uploaded")

    # Not required with any custom AMI
    if not cloudsim_stable:
        #
        #  Upload cloudsim.zip
        #
        upload_cloudsim(constellation_name,
                                   website_distribution,
                                   key_prefix)

    else:
        out = ssh_cli.cmd('sudo restart cloudsimd')
        log("\t%s" % out)

    # Upload the installed apache2.conf from the papa cloudsim so that the
    # junior cloudsim is configured the same way (e.g., uses basic auth instead
    # of openid).
    ssh_cli.upload_file('/etc/apache2/apache2.conf',
                        'cloudsim/distfiles/apache2.conf')

    ssh_cli.cmd('cp /home/ubuntu/cloudsim_users cloudsim/distfiles/users')
    # Deploy
    log("Deploying the cloudsim web app")
    deploy_script_fname = "/home/ubuntu/cloudsim/deploy.sh -f"
    out_s = ssh_cli.cmd("bash " + deploy_script_fname)
    log("\t%s" % out_s)

    # Copy in the htpasswd file, for use with basic auth.
    out_s = ssh_cli.cmd('sudo cp /home/ubuntu/cloudsim_htpasswd '
                        '/var/www-cloudsim-auth/htpasswd')
    log("\t%s" % out_s)

    # For a CloudSim launch, we look at the tags for a configuration to launch
    # at the end.
    if auto_launch_configuration:
        msg = ("Launching a constellation"
               " of type \"%s\"" % auto_launch_configuration)
        log(msg)
        constellation.set_value(LAUNCH_MSG_KEY, msg)
        time.sleep(20)
        ssh_cli.cmd("/home/ubuntu/cloudsim/launch.py"
                    " \"%s\" \"%s\"" % (username, auto_launch_configuration))

    print ("\033[1;32mCloudSim ready. Visit http://%s \033[0m\n" % ip)
    print ("Stop your CloudSim using the AWS console")
    print ("     http://aws.amazon.com/console/\n")

    constellation.set_value(STATE_KEY, 'running')
    constellation.set_value('constellation_state', 'running')
    time.sleep(10)
    constellation.set_value(LAUNCH_MSG_KEY, "Complete")
    log("provisioning done")


def terminate(constellation_name):

    constellation = ConstellationState(constellation_name)
    constellation.set_value(LAUNCH_MSG_KEY, "terminating")
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value(STATE_KEY, 'terminating')

    log("terminate %s [constellation_name=%s]" % (CONFIGURATION,
                                                  constellation_name))
    constellation_directory = constellation.get_value(
                                                    "constellation_directory")
    credentials_fname = os.path.join(constellation_directory,
                                     'credentials.txt')
    constellation.set_value("launch_stage", "nothing")

    cloud_provider = constellation.get_value("cloud_provider")
    if cloud_provider == 'aws':
        terminate_aws_server(constellation_name, credentials_fname)
    elif cloud_provider == 'openstack':
        openstack_creds = get_nova_creds()
        terminate_openstack_server(constellation_name, openstack_creds)
    elif cloud_provider == 'softlayer':
        constellation_prefix = constellation_name.split("OSRF_CloudSim_")[1]
        machine_name = "cs-%s" % constellation_prefix
        terminate_dedicated_sl_server(constellation_name,
                                      machine_name,
                                      credentials_fname)

    constellation.set_value(STATE_KEY, "terminated")
    constellation.set_value(LAUNCH_MSG_KEY, "terminated")
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

        test_name = "cs_test_"
        # self.constellation_name = 'CloudSim_test'
        self.constellation_name = get_unique_short_name(test_name + "_")
        self.constellation_directory = os.path.abspath(
                                        os.path.join(get_test_path(test_name),
                                        self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
        os.makedirs(self.constellation_directory)

        self.username = "toto@osrfoundation.org"
        CONFIGURATION = 'CloudSim-stable'
        self.tags.update({'TestCase': CONFIGURATION,
                      'configuration': CONFIGURATION,
                      'constellation': self.constellation_name,
                      'username': self.username,
                      'GMT': "now",
                      'cloud_provider': 'aws',
                      'constellation_directory': self.constellation_directory,
                      })

        # config = get_cloudsim_config()
        creds_fname = get_boto_path()
        dst = os.path.join(self.constellation_directory, "credentials.txt")
        shutil.copy(creds_fname, dst)

        test_name = "test_" + CONFIGURATION

        constellation = ConstellationState(self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory",
                                self.constellation_directory)
        constellation.set_value("configuration", CONFIGURATION)
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)

        launch(self.constellation_name, self.tags)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.constellation_name, i)

            time.sleep(1)

        terminate(self.constellation_name)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
