from __future__ import print_function

import unittest
import os
import time
import commands

import tempfile
import shutil
import redis
import logging

from launch_utils import get_unique_short_name


from launch_utils import SshClient



from launch_utils import ConstellationState # launch_db

from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_cloudsim_startup_script


from launch_utils.testing import get_test_runner, get_test_path
from launch_utils.testing import get_boto_path
from launch_utils.monitoring import  constellation_is_terminated, monitor_cloudsim_ping,\
    monitor_launch_state

from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue

from launch_utils.softlayer import load_osrf_creds,\
    reload_servers, wait_for_server_reloads, get_machine_login_info
from vrc_contest import ReloadOsCallBack, add_ubuntu_user_to_router,\
    create_private_machine_zip
from launch_utils.launch_db import get_cloudsim_config
 

CONFIGURATION = "cloudsim"

CLOUDSIM_ZIP_PATH= '/var/www-cloudsim-auth/cloudsim.zip'

def log(msg, channel = "cloudsim"):
    try:
        redis_client = redis.Redis()
        redis_client.publish(channel, msg)
        logging.info(msg)
        print("cloudsim> %s" % msg)
    except:
        print("Warning: redis not installed.")
    #print("cloudsim log> %s" % msg)

def start_task(constellation, package_name, launch_file_name,
               timeout, launch_args, latency, data_cap):
    
    for i in range(10):
        log("*****")
    log(" start_task constellation %s, package_name %s, launch_file_name %s, timeout %s, launch_args %s, latency %s, data_cap %s" % 
        (constellation, package_name, launch_file_name, timeout, launch_args, latency, data_cap) )


def get_softlayer_path():
    config =get_cloudsim_config()
    osrf_creds_fname = config['softlayer_path']
    return osrf_creds_fname


def stop_task(constellation):
    log("** STOP TASK %s ***" % constellation)


def monitor(username, constellation_name, counter):
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True

    constellation = ConstellationState(constellation_name)

    simulation_state = constellation.get_value('simulation_state')

    constellation_directory= constellation.get_value("constellation_directory")
    ip = constellation.get_value("simulation_ip" )
    log("%s simulation machine ip %s" % (constellation_name, ip))
    ssh_sim = SshClient(constellation_directory, "key-cs", 'ubuntu', ip)

    monitor_cloudsim_ping(constellation_name, 'simulation_ip', 'simulation_latency')
    monitor_launch_state(constellation_name, ssh_sim, simulation_state, "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg')
    return False

launch_sequence = ["nothing", "os_reload", "init", "zip",  "change_ip", "startup", "reboot", "running"]


def reload_os(constellation_name, constellation_prefix, osrf_creds_fname):

    constellation = ConstellationState(constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('os_reload'):
        return

    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('simulation_state', 'network_setup')
    constellation.set_value('simulation_aws_state', 'pending')
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('simulation_latency', '[]')
    constellation.set_value('sim_zip_file', 'not ready')
    constellation.set_value("error", "")

    constellation.set_value("gazebo", "not running")
    constellation.set_value('simulation_glx_state', "not running")

    osrf_creds = load_osrf_creds(osrf_creds_fname)
    # compute the softlayer machine names
    machine_names = ["cs-%s" % constellation_prefix]
    pub_ip, priv_ip, password = get_machine_login_info(osrf_creds, machine_names[0]) 
    log("reload os for machine %s [%s / %s] password %s " % (machine_names[0], pub_ip, priv_ip, password) )
    reload_servers(osrf_creds, machine_names)
    constellation.set_value("launch_stage", "os_reload")


def initialize_ubuntu_user(constellation_name, constellation_prefix, osrf_creds_fname, constellation_directory):
    constellation = ConstellationState( constellation_name)

    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('init'):
        return

    if os.path.exists(constellation_directory):
        shutil.rmtree(constellation_directory)
    os.makedirs(constellation_directory)

    machines_dict = {'cs-%s' % constellation_prefix:'simulation_launch_msg'}

    osrf_creds = load_osrf_creds(osrf_creds_fname)    
    reload_monitor = ReloadOsCallBack(constellation_name, machines_dict)
    wait_for_server_reloads(osrf_creds, machines_dict.keys(), reload_monitor.callback)
    constellation.set_value('simulation_aws_state', 'running')
    constellation.set_value('simulation_state', 'packages_setup')
    name = "cs-%s" % constellation_prefix

    pub_ip, priv_ip, password = get_machine_login_info(osrf_creds, name) 
    log("ubuntu user setup for machine cs %s [%s / %s] " % (name, pub_ip, priv_ip) )
    # dst_dir = os.path.abspath('.')

    log("machine details cs %s %s : %s" % (name, pub_ip, password))
    add_ubuntu_user_to_router(pub_ip, password, constellation_directory, 'key-cs')
    constellation.set_value("launch_stage", "init")


def create_zip(constellation_name):
    constellation = ConstellationState(constellation_name)
    constellation_directory = constellation.get_value("constellation_directory")
    fname_zip = os.path.join(constellation_directory, "cs","%s_%s.zip" % ("cs", constellation_name))

    launch_stage = constellation.get_value("launch_stage")
    
    if launch_sequence.index(launch_stage) >= launch_sequence.index('zip'):
        return fname_zip
    
    log("constellation name %s" % constellation_name)
    constellation = ConstellationState(constellation_name)
    ip = constellation.get_value("simulation_ip" )

    constellation_directory = constellation.get_value("constellation_directory")
    create_private_machine_zip("cs", ip, constellation_name, constellation_directory)
    constellation.set_value('sim_zip_file', 'ready')
    constellation.set_value("launch_stage", "zip")
    return fname_zip

def startup_script(constellation_name):
    constellation = ConstellationState( constellation_name)
    launch_stage = constellation.get_value("launch_stage")
    if launch_sequence.index(launch_stage) >= launch_sequence.index('startup'):
        return

    constellation_directory = constellation.get_value('constellation_directory')

    ip = constellation.get_value("simulation_ip" )
    ssh_client = SshClient(constellation_directory, "key-cs", 'ubuntu', ip)   
    
    local_fname = os.path.join(constellation_directory, 'cs_startup.bash')
    script = get_cloudsim_startup_script()
    with open(local_fname, 'w') as f:
        f.write(script)

    remote_fname = "startup_script.bash"
    ssh_client.upload_file(local_fname, remote_fname)
    # load packages onto router
    ssh_client.cmd("nohup sudo bash startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &")
    # load packages onto fc1

    constellation.set_value("launch_stage", "startup")


def launch(username, configuration, constellation_name, tags, constellation_directory, website_distribution = CLOUDSIM_ZIP_PATH ):

    cfg = get_cloudsim_config()
    osrf_creds_fname = cfg['softlayer_path']

    constellation_prefix = constellation_name.split("OSRF_CloudSim_")[1]

    log('launch!!! tags = %s' % tags)
    constellation = ConstellationState(constellation_name)

    constellation.set_value("simulation_launch_msg", "launching")
    constellation.set_value('simulation_state', 'starting')
    if not constellation.has_value("launch_stage"):
        constellation.set_value("launch_stage", "nothing") # "os_reload"
        #constellation.set_value("launch_stage", "os_reload")

    osrf_creds = load_osrf_creds(osrf_creds_fname)    
    pub_ip, priv_ip, password = get_machine_login_info(osrf_creds, "cs-%s" % constellation_prefix) 
    log("reload os for machine [%s / %s] password %s " % (pub_ip, priv_ip, password))
    constellation.set_value("simulation_ip", pub_ip )

    auto_launch_configuration = None
    if tags.has_key('args'):
        auto_launch_configuration = tags['args']

    log('auto_launch_configuration %s' % auto_launch_configuration)
    constellation.set_value("simulation_launch_msg", "waiting for Operating System reload")
    reload_os(constellation_name, constellation_prefix, osrf_creds_fname)

    constellation.set_value("simulation_launch_msg", "seting up user accounts and keys")
    initialize_ubuntu_user(constellation_name, constellation_prefix, osrf_creds_fname, constellation_directory)
    constellation.set_value("simulation_launch_msg", "create zip file")
    log("create zip")
    fname_zip = create_zip(constellation_name)

    #create a copy for downloads
    local_zip = os.path.join(constellation_directory, "CloudSim.zip")
    shutil.copy(fname_zip, local_zip)

    log("install packages")
    constellation.set_value("simulation_launch_msg", "install packages")
    startup_script(constellation_name)

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")

    ip = constellation.get_value("simulation_ip" )
    clean_local_ssh_key_entry(ip)
    
    constellation.set_value('simulation_ip', ip)
    log("%s simulation machine ip %s" % (constellation_name, ip))
    ssh_sim = SshClient(constellation_directory, "key-cs", 'ubuntu', ip)
    
    constellation.set_value('simulation_launch_msg', "waiting for network")
    networking_done = get_ssh_cmd_generator(ssh_sim,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([networking_done], sleep=2)


    constellation.set_value('simulation_launch_msg', "creating monitoring scripts")
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

    constellation.set_value('simulation_launch_msg', "waiting for packages to install")
    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([sim_setup_done], sleep=2)

    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/ubuntu/%s" % ( short_file_name)
    log("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )

    constellation.set_value('simulation_launch_msg', "uploading CloudSim distribution")
    out = ssh_sim.upload_file(website_distribution, remote_fname)
    log(" upload: %s" % out)
    constellation.set_value('simulation_launch_msg', "uploading web app")
    #upload_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'running' ,max_retries = 100)
    #empty_ssh_queue([upload_done], sleep=2)

    constellation.set_value('simulation_launch_msg', "unzip web app")
    log("unzip web app")
    out = ssh_sim.cmd("unzip -o " + remote_fname )
    log ("\t%s"% out)

    log("Setup admin user %s" % username)
    add_user_cmd = 'echo \'{"%s":"admin"}\' > cloudsim/distfiles/users' % username 
    log("add user to cloudsim: %s" % add_user_cmd)
    out = ssh_sim.cmd(add_user_cmd)
    log ("\t%s"% out)

    # fname_zip = os.path.join(constellation_directory, "cs","cs.zip")
    log("Uploading the key file to the server")
    remote_fname = "/home/ubuntu/cloudsim/cloudsim_ssh.zip"
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname) )
    out = ssh_sim.upload_file(fname_zip , remote_fname)
    log ("\t%s"% out)

    if os.path.exists(osrf_creds_fname):
        constellation.set_value('simulation_launch_msg', "Uploading the SoftLayer credentials to the server")
        remote_fname = "/home/ubuntu/softlayer.json" 
        log("uploading '%s' to the server to '%s'" % (osrf_creds_fname, remote_fname) )
        out = ssh_sim.upload_file(osrf_creds_fname , remote_fname)
        log ("\t%s"% out)
    else:
        constellation.set_value('simulation_launch_msg',"No SoftLayer credentials loaded")

    ec2_creds_fname = cfg['boto_path']    
    if os.path.exists(ec2_creds_fname):
        # todo ... set the name, upload both files
        constellation.set_value('simulation_launch_msg',"Uploading the ec2 credentials to the server")
        remote_fname = "/home/ubuntu/boto.ini" 
        log("uploading '%s' to the server to '%s'" % (ec2_creds_fname, remote_fname) )
        out = ssh_sim.upload_file(ec2_creds_fname , remote_fname)
        log ("\t%s"% out)
    else:
        constellation.set_value('simulation_launch_msg',"No Amazon Web Services credentials loaded")

    cloudsim_portal_key_fname = cfg['cloudsim_portal_key_path']
    cloudsim_portal_json_fname = cfg['cloudsim_portal_json_path']
    if os.path.exists(cloudsim_portal_key_fname) and os.path.exists(cloudsim_portal_json_fname):
        constellation.set_value('simulation_launch_msg',"Uploading the Portal key to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.key" 
        log("uploading '%s' to the server to '%s'" % (cloudsim_portal_key_fname, remote_fname) )
        out = ssh_sim.upload_file(cloudsim_portal_key_fname, remote_fname)
        log ("\t%s"% out)

        constellation.set_value('simulation_launch_msg',"Uploading the Portal JSON file to the server")
        remote_fname = "/home/ubuntu/cloudsim_portal.json" 
        log("uploading '%s' to the server to '%s'" % (cloudsim_portal_json_fname, remote_fname) )
        out = ssh_sim.upload_file(cloudsim_portal_json_fname, remote_fname)
        log ("\t%s"% out)
    else:
        constellation.set_value('simulation_launch_msg',"No portal key or json file found")

    bitbucket_key_fname = cfg['cloudsim_bitbucket_key_path']
    if os.path.exists(bitbucket_key_fname):
        # todo ... set the name, upload both files
        constellation.set_value('simulation_launch_msg',"Uploading the bitbucket key to the server")
        remote_fname = "/home/ubuntu/cloudsim_bitbucket.key"
        log("uploading '%s' to the server to '%s'" % (bitbucket_key_fname, remote_fname) )
        out = ssh_sim.upload_file(ec2_creds_fname , remote_fname)
        log ("\t%s"% out)
    else:
        constellation.set_value('simulation_launch_msg',"No bitbucket key uploaded")

    constellation.set_value('simulation_launch_msg', "deploying web app")
    # out =machine.ssh_send_command('echo %s > cloudsim/distfiles/users' % username)
    log("Deploying the cloudsim web app")
    # Pass -f to force deploy.sh to overwrite any existing users file
    deploy_script_fname = "/home/ubuntu/cloudsim/deploy.sh -f" 
    log("running deploy script '%s' remotely" % deploy_script_fname)
    out = ssh_sim.cmd("bash " + deploy_script_fname  )
    log ("\t%s"% out)


    #
    # For a CLoudSim launch, we look at the tags for a configuration to launch
    # at the end.
    if auto_launch_configuration:

        msg = "Launching a constellation of type \"%s\"" % auto_launch_configuration
        log(msg)
        constellation.set_value('simulation_launch_msg', msg)
        ssh_sim.cmd("/home/ubuntu/cloudsim/launch.py \"%s\" \"%s\"" % (username, auto_launch_configuration) )
        time.sleep(5)
    
    print ("\033[1;32mCloudSim ready. Visit http://%s \033[0m\n"% ip)
    print ("Stop your CloudSim using the AWS console")
    print ("     http://aws.amazon.com/console/\n")

    constellation.set_value('simulation_launch_msg', "Complete")     
    constellation.set_value('simulation_state', 'running')
    constellation.set_value('constellation_state', 'running')
    log("provisioning done")



def terminate(username,  constellation_name, constellation_directory):

    # osrf_creds_fname = get_softlayer_path()
    
    constellation = ConstellationState( constellation_name)
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('simulation_state', 'terminating')
    log("terminate %s [constellation_name=%s]" % (CONFIGURATION, constellation_name) )
    
    constellation.set_value('simulation_aws_state', 'terminated')  
    constellation.set_value('simulation_state', "terminated")
    constellation.set_value('simulation_launch_msg', "terminated")

    time.sleep(5.0)
    constellation.set_value('constellation_state', 'terminated')
    


def cloudsim_bootstrap(username, credentials_ec2, initial_constellation):

    constellation_name = get_unique_short_name('c')
    
    gmt = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())
    tags = {'GMT': gmt, 
            'username':username,
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
    
    return launch(username, constellation_name, tags,  credentials_ec2,
                  constellation_directory, website_distribution)
    
    
def zip_cloudsim():
    
    tmp_dir = tempfile.mkdtemp("cloudsim")
    tmp_zip = os.path.join(tmp_dir, "cloudsim.zip")
    full_path_of_cloudsim = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Account for having a version in the name of the directory, which we
    # want to get rid of
    shutil.copytree(full_path_of_cloudsim, os.path.join(tmp_dir, 'cloudsim'))
    os.chdir(tmp_dir)
    commands.getoutput('zip -r %s cloudsim'%(tmp_zip))
  
    return tmp_zip
    
    
class CloudsimBootStrapTestCase(unittest.TestCase):
    
    def setUp(self):
        self.ec2 = None
       
    #def test_cloudsim_zip(self):
    #    print ('zip cloudsim')
        
    #    zip_path = zip_cloudsim()
    #    self.assert_(os.path.exists(zip_path), "no zip done!")
    #    shutil.rmtree(os.path.dirname(zip_path))
        
    def test_cloudsim_bootstrap(self):        
        self.ec2 = get_boto_path()
        self.simulation_aws_id, sim_ip, key_filename = cloudsim_bootstrap("test@osrfoundation.org", self.ec2, None)        
        
        

class JustInCase(unittest.TestCase):
    
    
    
    def test_launch(self):
        
        launch_stage = None # use the current stage
        launch_stage = "nothing" 
        launch_stage = "os_reload"
        #"nothing", "os_reload", "init_router", "init_privates", "zip",  "change_ip", "startup", "reboot", "running"
        self.tags = {}
         
        
        self.constellation_name = 'OSRF CloudSim 01' 
        self.username = "toto@osrfoundation.org"
        CONFIGURATION = 'cloudsim'
        self.tags.update({'TestCase':CONFIGURATION, 'configuration': 'cloudsim', 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"})
        
        
        self.credentials_softlayer  = get_softlayer_path()
        
        test_name = "test_" + CONFIGURATION

        if not self.constellation_name:
            self.constellation_name =  get_unique_short_name(test_name + "_")
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))
            #  print("creating: %s" % self.constellation_directory )
            os.makedirs(self.constellation_directory)
        else:
            self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))

        constellation = ConstellationState( self.constellation_name)
        constellation.set_value("constellation_name", self.constellation_name)
        constellation.set_value("constellation_directory", self.constellation_directory)
        constellation.set_value("configuration", 'cloudsim')
        constellation.set_value('current_task', "")
        constellation.set_value('tasks', [])

        log(self.constellation_directory)
        if launch_stage:
            constellation.set_value("launch_stage", launch_stage)

        launch(self.username, "CloudSim", self.constellation_name, self.tags, self.credentials_softlayer, self.constellation_directory)

        sweep_count = 2
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_softlayer, i)
            time.sleep(1)

        terminate(self.constellation_name, self.credentials_softlayer, self.constellation_directory)


if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       
