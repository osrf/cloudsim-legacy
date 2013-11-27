from __future__ import print_function

import unittest
import os
import time
import commands
import json
import tempfile
import shutil


from launch_utils import SshClient
from launch_utils import ConstellationState  # launch_db
from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_cloudsim_startup_script
from launch_utils.monitoring import constellation_is_terminated
from launch_utils.monitoring import monitor_cloudsim_ping
from launch_utils.monitoring import monitor_launch_state
from launch_utils.ssh_queue import get_ssh_cmd_generator, empty_ssh_queue
from launch_utils.launch_db import log_msg, get_cloudsim_version
from launch_utils.launch_db import LaunchException
from vrc_contest import create_private_machine_zip
from launch_utils.openstack import acquire_openstack_server
from launch_utils.openstack import terminate_openstack_server
from launch_utils.openstack import get_nova_creds
from launch_utils.sl_cloud import acquire_dedicated_sl_server
from launch_utils.sl_cloud import terminate_dedicated_sl_server
from launch_utils.aws import acquire_aws_single_server
from launch_utils.aws import terminate_aws_server
from launch_utils.launch_db import get_unique_short_name
from launch_utils.launch_db import init_constellation_data


CONFIGURATION = "cloudsim"

LAUNCH_MSG_KEY = "cs_launch_msg"
STATE_KEY = 'cs_state'
IP_KEY = "cs_public_ip"
LATENCY_KEY = 'cs_latency'
ZIP_READY_KEY = 'cs_zip_file'

LAUNCH_MSG_KEY = "cs_launch_msg"
STATE_KEY = 'cs_state'
IP_KEY = "cs_public_ip"
LATENCY_KEY = 'cs_latency'
ZIP_READY_KEY = 'cs_zip_file'


def log(msg, channel=__name__, severity='info'):
    log_msg(msg, channel, severity)


def update(constellation_name, force_authentication_type=None):
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

    constellation_directory = constellation.get_value(
                                                     'constellation_directory')
    # zip the currently running software
    website_distribution = _get_cloudsim_src_tarball(constellation_directory)
    # send to cloudsim machine
    _upload_cloudsim(constellation_name, website_distribution)
    ip_address = constellation.get_value(IP_KEY)
    ssh_cli = SshClient(constellation_directory,
                        "key-cs",
                        'ubuntu',
                        ip_address)

    log("Deploying the cloudsim web app")
    deploy_cmd = __get_deploy_cmd(force_authentication_type, reset_db=False)
    out_s = ssh_cli.cmd(deploy_cmd)
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


def _upload_cloudsim(constellation_name, website_distribution):
    constellation = ConstellationState(constellation_name)
    constellation_dir = constellation.get_value('constellation_directory')

    ip_address = constellation.get_value(IP_KEY)
    ssh_cli = SshClient(constellation_dir, "key-cs", 'ubuntu', ip_address)
    remote_filename = "/home/ubuntu/cloudsim.zip"

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


def __get_deploy_cmd(force_authentication_type=None, reset_db=False):
    """
    Computes the deploy.sh argument. If force_authentication_type is None, then
    the authentication type is inferred from the currently installed CloudSim.

    If CloudSim is not be installed, force_authentication_type should be either
    "" for OpenID, or "Basic" for basic authentication

    "-b" for basic authentication
    "-f" for new installation (wipes the Redis db and users)
    """
    def get_current_authentication_type():
        """
        Checks that CloudSim server is installed and determines the
        authentication method
        """
        try:
            r = commands.getoutput('grep Alias /etc/apache2/apache2.conf')
            # make sure that cloudsim is installed
            r.index("cloudsim")
            r = commands.getoutput('grep AuthType /etc/apache2/apache2.conf')
            auth_type = r.split("AuthType")[1].strip()
            return auth_type
        except:
            raise LaunchException('CloudSim web app is not installed')

    auth_type = force_authentication_type
    if not auth_type:
        auth_type = get_current_authentication_type()

    deploy_args = ""  # the default for OpenID
    if auth_type == "Basic":
        deploy_args = "-b"
    if reset_db:
        deploy_args = "-f " + deploy_args
    deploy_cmd = "bash /home/ubuntu/cloudsim/deploy.sh %s" % deploy_args
    return deploy_cmd


def launch(constellation_name,
           tags,
           force_authentication_type=None,
           basic_auth_password=None):
    """
    The
    force_authentication_type can be None, 'OpenID' or 'Basic'
    """

    log("CloudSim launch %s" % constellation_name)
    constellation = ConstellationState(constellation_name)

    cloudsim_stable = True
    if constellation.get_value('configuration') == 'CloudSim':
        cloudsim_stable = False

    # we won't upload the CloudSim code if we're launching a stable version
    upload_cloudsim_code = cloudsim_stable == False

    script = None
    image_key = None

    if not cloudsim_stable:
        script = script = get_cloudsim_startup_script()
        image_key = 'ubuntu_1204_x64'
    else:
        script = ''
        image_key = 'ubuntu_1204_x64_cloudsim_stable'

    log("cloudsim launch tags %s" % (tags))
    cloud_provider = tags['cloud_provider']
    username = tags['username']
    #constellation_name = tags['constellation_name']
    constellation_directory = tags['constellation_directory']
    credentials_fname = os.path.join(constellation_directory,
                                     'credentials.txt')

    machine_prefix = "cs"
    # cfg = get_cloudsim_config()

    log('launch!!! tags = %s' % tags)

    constellation.set_value(LAUNCH_MSG_KEY, "launching")
    constellation.set_value(STATE_KEY, 'starting')
    constellation.set_value("launch_stage", "nothing")
    constellation.set_value(LATENCY_KEY, '[]')

    constellation.set_value(STATE_KEY, 'network_setup')

    constellation.set_value(LAUNCH_MSG_KEY, "starting")
    constellation.set_value(LATENCY_KEY, '[]')
    constellation.set_value(ZIP_READY_KEY, 'not ready')
    constellation.set_value("error", "")

    constellation.set_value("gazebo", "not running")
    constellation.set_value('sim_glx_state', "not running")

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
        openstack_creds = credentials_fname
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
    users = {username: "admin"}
    fname_users = os.path.join(constellation_directory, "cloudsim_users")
    with open(fname_users, 'w') as f:
        s = json.dumps(users)
        f.write(s)
    remote_fname = "/home/ubuntu/cloudsim_users"
    log("uploading '%s' to the server to '%s'" % (fname_users, remote_fname))
    out = ssh_cli.upload_file(fname_users, remote_fname)
    log("\t%s" % out)
    # Add the currently logged-in user to the htpasswd file on the cloudsim
    psswds = {}
    psswds[username] = "%s" % constellation_name
    if basic_auth_password:
        psswds[username] = basic_auth_password
    ssh_cli.cmd('touch cloudsim_htpasswd')
    for user, psswd in psswds.items():
        htpasswd_cmd = 'htpasswd -b cloudsim_htpasswd %s %s' % (user, psswd)
        log("add current user to htpasswd file: %s" % htpasswd_cmd)
        out = ssh_cli.cmd(htpasswd_cmd)
        log("\t%s" % out)

    constellation.set_value(LAUNCH_MSG_KEY,
                            "Uploading the key file to the server")
    remote_fname = "/home/ubuntu/cloudsim/cloudsim_ssh.zip"
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname))
    out = ssh_cli.upload_file(fname_zip, remote_fname)
    log("\t%s" % out)

    ec2_creds_fname = credentials_fname
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

    if upload_cloudsim_code:
        #  Upload source zip
        website_distribution = _get_cloudsim_src_tarball(
                                                       constellation_directory)
        _upload_cloudsim(constellation_name, website_distribution)

    ssh_cli.cmd('cp /home/ubuntu/cloudsim_users cloudsim/distfiles/users')

    # Determine the current authentication type, and deploy the same
    # or use the force_authentication_type

    # Deploy
    log("Deploying the cloudsim web app")
    deploy_cmd = __get_deploy_cmd(force_authentication_type, reset_db=True)
    out_s = ssh_cli.cmd(deploy_cmd)
    log("\t%s" % out_s)

    # Copy in the htpasswd file, for use with basic auth.
    out_s = ssh_cli.cmd('sudo cp /home/ubuntu/cloudsim_htpasswd '
                        '/var/www-cloudsim-auth/htpasswd')
    log("\t%s" % out_s)
    print ("\033[1;32mCloudSim ready. Visit http://%s \033[0m\n" % ip)
    print ("Stop your CloudSim using the AWS console")
    print ("     http://aws.amazon.com/console/\n")

    constellation.set_value(STATE_KEY, 'running')
    constellation.set_value('constellation_state', 'running')
    time.sleep(10)
    constellation.set_value(LAUNCH_MSG_KEY, "Complete")
    log("provisioning done")
    return ip


def terminate(constellation_name):

    constellation = ConstellationState(constellation_name)
    constellation.set_value(LAUNCH_MSG_KEY, "terminating")
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


def zip_cloudsim_src(target_fname):
    """
    Create a zip file of the current source tree. This function cannot
    be called from an installed CloudSim, since the web app source is not
    present
    """
    full_path_of_cloudsim = os.path.dirname(
                                    os.path.dirname(
                                    os.path.dirname(
                                    os.path.abspath(__file__))))

    tmp_dir = tempfile.mkdtemp("cloudsim")
    cloudsim_dir = os.path.join(tmp_dir, 'cloudsim')
    shutil.copytree(full_path_of_cloudsim, cloudsim_dir)
    # remove test files if present (this avoids bloat)
    test_dir = os.path.join(cloudsim_dir, "test-reports")
    if os.path.isdir(test_dir):
        shutil.rmtree(test_dir)
    hg_dir = os.path.join(cloudsim_dir, ".hg")
    if os.path.isdir(hg_dir):
        shutil.rmtree(hg_dir)
    # zip files
    os.chdir(tmp_dir)
    commands.getoutput('zip -r cloudsim.zip cloudsim')
    # move zip file to destination
    shutil.move(os.path.join(tmp_dir, "cloudsim.zip"), target_fname)
    shutil.rmtree(tmp_dir)


def _get_cloudsim_src_tarball(target_dir, short_fname="cloudsim_src.zip"):
    """
    creates a zipped cloudsim directory and returns
    a path to a cloudsim.zip in a temp directory. This is the
    CloudSim source tarball that gets deployed in launched instances.
    """
    target_fname = os.path.join(target_dir, short_fname)
    # locate source files
    # in the case that this call is made from a running cloudsim, the zip
    # file already exists (created by deploy.sh)
    # this is likely a baby cloudsim launch
    if __file__.startswith("/var/cloudsimd/"):
        src = "/var/www-cloudsim-auth/cloudsim.zip"
        log("_get_cloudsim_src_tarball copying %s to %s" % (src, target_fname))
        shutil.copy2(src, target_fname)
    # if the call is made from the source tree, the zipping must be done
    # this is likely a create_cloudsim call
    else:
        log("_get_cloudsim_src_tarball creating zip %s" % (target_fname))
        zip_cloudsim_src(target_fname)
    return target_fname


def create_cloudsim(username,
                    credentials_fname,
                    configuration,
                    authentication_type,  # "OpenID" or "Basic"
                    password,
                    data_dir,
                    constellation_name):
    """
    Launches a CloudSim directly (without using the CloudSimd daemon)

    It returns the ip address of the cloudsim instance created.
    Supports Google OpenID and Basic Authentication:
    authentication_type should be "OpenID" or "Basic"
    and password should not be None when "Basic" authentication is used
    """
    config = {}
    config['cloudsim_version'] = get_cloudsim_version()
    config['boto_path'] = credentials_fname
    config['machines_directory'] = data_dir

    data = {}
    data['username'] = username
    data['cloud_provider'] = 'aws'
    data['configuration'] = configuration

    init_constellation_data(constellation_name, data, config)

    # Launch a cloudsim instance
    cloudsim_ip = launch(constellation_name,
                         tags=data,
                         force_authentication_type=authentication_type,
                         basic_auth_password=password)
    # update CloudSim if we started from a stable release
    if configuration.find("stable") > 0:
        update(constellation_name, authentication_type)
    return cloudsim_ip


class TestCreateCloudSim(unittest.TestCase):

    def setUp(self):
        from launch_utils.testing import get_boto_path
        from launch_utils.testing import get_test_path

        self.name = get_unique_short_name('tcc')
        self.data_dir = get_test_path("create_cs_test")

        self.ip = create_cloudsim(username="test",
                                  credentials_fname=get_boto_path(),
                                  configuration="CloudSim-stable",
                                  authentication_type="Basic",
                                  password="test123",
                                  data_dir=self.data_dir,
                                  constellation_name=self.name)
        print("cloudsim %s created" % self.ip)

    def test(self):
        sweep_count = 10

        for i in range(sweep_count):
            print("monitoring %s/%s" % (i, sweep_count))
            monitor(self.name, i)

    def tearDown(self):
        print("terminate cloudsim %s" % self.ip)
        terminate(self.name)
        constellation = ConstellationState(self.name)
        constellation.expire(1)


if __name__ == "__main__":
    from launch_utils.testing import get_test_runner
    xmlTestRunner = get_test_runner()
    unittest.main(testRunner=xmlTestRunner)
