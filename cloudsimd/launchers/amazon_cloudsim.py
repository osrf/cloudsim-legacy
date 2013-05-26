from __future__ import print_function

import unittest
import os
import time
import commands
import zipfile

import boto
from boto.pyami.config import Config as BotoConfig


from launch_utils import get_unique_short_name
#from launch_utils import wait_for_multiple_machines_to_run 
from launch_utils import wait_for_multiple_machines_to_terminate
from launch_utils import get_ec2_instance 
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient



from launch_utils import ConstellationState # launch_db

from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_cloudsim_startup_script, \
    create_ssh_connect_file

from launch_utils.launch import LaunchException, aws_connect, get_amazon_amis


from launch_utils.testing import get_test_runner
from launch_utils.testing import get_boto_path, get_test_path
from launch_utils.monitoring import record_ping_result, LATENCY_TIME_BUFFER,\
    machine_states, get_aws_states, constellation_is_terminated,\
    update_machine_aws_states, get_ssh_client, monitor_cloudsim_ping,\
    monitor_launch_state

from launch_utils.task_list import get_ssh_cmd_generator, empty_ssh_queue
import tempfile
import shutil
import redis
import logging
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


def update(constellation_name):
    """
    Upadate the constellation software on the servers.
    This function is a plugin function that should be implemented by 
    each constellation type
    """
    constellation = ConstellationState( constellation_name)
    constellation_directory = constellation.get_value('constellation_directory')
    
    # Do the software update here, via ssh
    
    
def start_task(constellation, package_name, launch_file_name,
               timeout, launch_args, latency, data_cap):
    
    for i in range(10):
        log("*****")
    log(" start_task constellation %s, package_name %s, launch_file_name %s, timeout %s, launch_args %s, latency %s, data_cap %s" % 
        (constellation, package_name, launch_file_name, timeout, launch_args, latency, data_cap) )
    
    
def stop_task(constellation):
    for i in range(10):
        log("** STOP TASK %s ***" % constellation)

def monitor(username, constellation_name, counter):
    
    
    time.sleep(1)
    if constellation_is_terminated(constellation_name):
        return True
    
    constellation = ConstellationState( constellation_name)
   
    simulation_state = constellation.get_value('simulation_state')
    update_machine_aws_states( constellation_name, {'simulation_aws_id':"simulation_aws_state"}) 
    
    ssh_sim = get_ssh_client(constellation_name, simulation_state,'simulation_ip', 'sim_key_pair_name' )

    monitor_cloudsim_ping(constellation_name, 'simulation_ip', 'simulation_latency')
    monitor_launch_state(constellation_name, ssh_sim, simulation_state, "bash cloudsim/dpkg_log_sim.bash", 'simulation_launch_msg')
    return False #log("monitor not done")    



def launch(username, configuration, constellation_name, tags, 
           constellation_directory, website_distribution=CLOUDSIM_ZIP_PATH ):

    log('launch!!! tags = %s' % tags)

    auto_launch_configuration = None
    if tags.has_key('args'):
        auto_launch_configuration  = tags['args']

    log('auto_launch_configuration %s' % auto_launch_configuration )

    ec2conn = aws_connect()[0]
    constellation = ConstellationState( constellation_name)

    constellation.set_value('constellation_state', 'launching')
    constellation.set_value('simulation_state', 'nothing')
    constellation.set_value('simulation_aws_state', 'nothing')
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('simulation_latency', '[]')
    constellation.set_value('sim_zip_file', 'not ready')

    constellation.set_value("gazebo", "not running")
    constellation.set_value('simulation_glx_state', "not running")

    sim_machine_name = "cloudsim_"+ constellation_name
    constellation.set_value('sim_machine_name', sim_machine_name)

    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    os.makedirs(sim_machine_dir)

    constellation.set_value('simulation_launch_msg',  "setting up security groups")
    sim_sg_name = 'sim-sg-%s'%(constellation_name) 

    log("Creating a security group")
    sim_security_group= ec2conn.create_security_group(sim_sg_name, "simulator security group for constellation %s" % constellation_name)
    sim_security_group.authorize('tcp', 80, 80, '0.0.0.0/0')   # web
    sim_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sim_security_group.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping       
    sim_security_group_id = sim_security_group.id
    log("Security group created")

    constellation.set_value('sim_security_group_id', sim_security_group_id)

    constellation.set_value('simulation_launch_msg', "creating ssh keys")
    sim_key_pair_name = 'key-sim-%s'%(constellation_name)
    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    key_pair = ec2conn.create_key_pair(sim_key_pair_name)
    key_pair.save(sim_machine_dir)

    amis = get_amazon_amis()
    aws_image = amis['ubuntu_1204_x64']

    SIM_SCRIPT = get_cloudsim_startup_script()
    roles_to_reservations ={}
    try:

        res = ec2conn.run_instances( image_id = aws_image, 
                                     instance_type = 't1.micro',
                                     #subnet_id      = subnet_id,
                                     #private_ip_address=SIM_IP,
                                     security_group_ids=[sim_security_group_id],
                                     key_name=sim_key_pair_name ,
                                     user_data=SIM_SCRIPT)

        roles_to_reservations['simulation_state'] = res.id

    except Exception, e:
        constellation.set_value("error", "%s" % e)
        raise

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")


    # running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries = 150, final_state = 'network_setup')
    running_machines = {}
    count =200
    done = False
    color = "yellow"
    while not done:
        log("attempt %s" % count)
        time.sleep(2)
        count -=1
        for r in ec2conn.get_all_instances():
            if count < 0:
                msg = "timeout while waiting for EC2 machine(s) %s" % sim_machine_name
                raise LaunchException(msg) 
            if r.id == res.id:
                state = r.instances[0].state 
                if  state == 'running':
                    aws_id = r.instances[0].id
                    running_machines['simulation_state'] = aws_id
                    constellation.set_value('simulation_state', 'network_setup')
                    done = True
                constellation.set_value("simulation_aws_state", state)

    simulation_aws_id = running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)

    sim_tags = {'Name':sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([ simulation_aws_id ], sim_tags)

    # ec2conn.associate_address(router_aws_id, allocation_id = eip_allocation_id)
    sim_instance = get_ec2_instance(ec2conn, simulation_aws_id)
    sim_ip = sim_instance.ip_address

    clean_local_ssh_key_entry(sim_ip)

    constellation.set_value('simulation_ip', sim_ip)
    log("%s simulation machine ip %s" % (constellation_name, sim_ip))
    ssh_sim = SshClient(sim_machine_dir, sim_key_pair_name, 'ubuntu', sim_ip)

    constellation.set_value('simulation_launch_msg', "waiting for network")
    networking_done = get_ssh_cmd_generator(ssh_sim,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", 'packages_setup' ,max_retries = 1000)
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


    constellation.set_value('simulation_launch_msg', "creating zip file bundle")
    key_filename = sim_key_pair_name + '.pem'
    fname_ssh_key =  os.path.join(sim_machine_dir, key_filename)
    os.chmod(fname_ssh_key, 0600)

    fname_ssh_sh =  os.path.join(sim_machine_dir,'ssh.bash')
    file_content = create_ssh_connect_file(key_filename, sim_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755)

    fname_zip = os.path.join(sim_machine_dir, "%s.zip" % sim_machine_name)
    #creating zip
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh]

    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(sim_machine_name, short_fname)
            fzip.write(fname, zip_name)

    constellation.set_value('sim_zip_file', 'ready')
    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'running' ,max_retries = 100)
    empty_ssh_queue([sim_setup_done], sleep=2)

    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/ubuntu/%s" % ( short_file_name)
    log("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )

    out = ssh_sim.upload_file(website_distribution, remote_fname)
    log(" upload: %s" % out)
    upload_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'running' ,max_retries = 100)
    empty_ssh_queue([upload_done], sleep=2)


    log("unzip web app")
    out = ssh_sim.cmd("unzip " + remote_fname )
    log ("\t%s"% out)

    log("Setup admin user %s" % username)
    add_user_cmd = 'echo \'{"%s":"admin"}\' > cloudsim/distfiles/users' % username 
    log("add user to cloudsim: %s" % add_user_cmd)
    out = ssh_sim.cmd(add_user_cmd)
    log ("\t%s"% out)

    log("Uploading the key file to the server")
    remote_fname = "/home/ubuntu/cloudsim/cloudsim_ssh.zip"
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname) )
    out = ssh_sim.upload_file(fname_zip , remote_fname)
    log ("\t%s"% out)


    config = get_cloudsim_config()
    credentials_ec2 = config['boto_path']
    osrf_creds_fname = config['softlayer_path']
    cloudsim_portal_key_fname = config['cloudsim_portal_key_path']
    cloudsim_portal_json_fname = config['cloudsim_portal_json_path']
    
    log("Uploading the ec2 credentials to the server")
    remote_fname = "/home/ubuntu/boto.ini" 
    log("uploading '%s' to the server to '%s'" % (credentials_ec2, remote_fname) )
    out = ssh_sim.upload_file(credentials_ec2, remote_fname)
    log ("\t%s"% out)

    log("Uploading the SoftLayer credentials to the server")
    remote_fname = "/home/ubuntu/softlayer.json" 
    log("uploading '%s' to the server to '%s'" % (osrf_creds_fname, remote_fname) )
    out = ssh_sim.upload_file(osrf_creds_fname, remote_fname)
    log ("\t%s"% out)
    
    log("Uploading the Portal key to the server")
    remote_fname = "/home/ubuntu/cloudsim_portal.key" 
    log("uploading '%s' to the server to '%s'" % (cloudsim_portal_key_fname, remote_fname) )
    out = ssh_sim.upload_file(cloudsim_portal_key_fname, remote_fname)
    log ("\t%s"% out)
    
    log("Uploading the Portal JSON file to the server")
    remote_fname = "/home/ubuntu/cloudsim_portal.json" 
    log("uploading '%s' to the server to '%s'" % (cloudsim_portal_json_fname, remote_fname) )
    out = ssh_sim.upload_file(cloudsim_portal_json_fname, remote_fname)
    log ("\t%s"% out)
    
    # out =machine.ssh_send_command('echo %s > cloudsim/distfiles/users' % username)
    log("Deploying the cloudsim web app")
    deploy_script_fname = "/home/ubuntu/cloudsim/deploy.sh" 
    log("running deploy script '%s' remotely" % deploy_script_fname)
    out = ssh_sim.cmd("bash " + deploy_script_fname  )
    log ("\t%s"% out)


    #
    # For a CLoudSim launch, we look at the tags for a configuration to launch
    # at the end.
    if auto_launch_configuration:
        log("Launching a constellation of type %s" % auto_launch_configuration)
        ssh_sim.cmd("/home/ubuntu/cloudsim/launch.py %s %s" % (username, auto_launch_configuration) )

    log('setup complete')

    print ("\033[1;32mCloudSim ready. Visit http://%s \033[0m\n"% sim_ip)
    print ("Stop your CloudSim using the AWS console")
    print ("     http://aws.amazon.com/console/\n")

    constellation.set_value('constellation_state', 'running')
    log("provisioning done")

    return simulation_aws_id, sim_ip, key_filename


def terminate( constellation_name):

    ec2conn = aws_connect()[0]
    constellation = ConstellationState( constellation_name)
    constellation.set_value('constellation_state', 'terminating')
    constellation_directory = constellation.get_value('constellation_directory')
    
    log("terminate %s [constellation_name=%s]" % (CONFIGURATION, constellation_name) )

    try:
        running_machines =  {}
        running_machines['simulation_aws_state'] = constellation.get_value('simulation_aws_id')

        wait_for_multiple_machines_to_terminate(ec2conn, 
                                                running_machines, 
                                                constellation, 
                                                max_retries = 150)

        constellation.set_value('simulation_state', "terminated")
        constellation.set_value('simulation_launch_msg', "terminated")

        print ('Waiting after killing instances...')
        time.sleep(10.0)
    except Exception, e:
        log ("error killing instances: %s" % e)

    try:
        sim_key_pair_name =  constellation.get_value('sim_key_pair_name')
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception, e:
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))

    try:
        security_group_id =  constellation.get_value('sim_security_group_id' )
        ec2conn.delete_security_group(group_id = security_group_id)
    except Exception, e:
        log("error cleaning up sim security group %s: %s" % (security_group_id, e))       

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
        
    def tearDown(self):       
        if self.ec2 != None:
            c = self.ec2
            ec2conn = aws_connect(c)[0]
            ec2conn.terminate_instances(instance_ids=[self.simulation_aws_id])


class DbCase(unittest.TestCase):
    
    def test_set_get(self):
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data(constellation, value, expiration)
        
        data = get_constellation_data(constellation)
        self.assert_(data['a'] == value['a'], "redis db value not set")
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       
