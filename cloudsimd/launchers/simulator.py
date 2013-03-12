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
from launch_utils import log
from launch_utils import set_constellation_data
from launch_utils import get_constellation_data
from launch_utils import SshClient



from launch_utils import get_ssh_cmd_generator, empty_ssh_queue # task_list
from launch_utils import ConstellationState # launch_db
from launch_utils.launch_events import latency_event, launch_event, gl_event,\
    simulator_event, machine_state_event, parse_dpkg_line

from launch_utils.sshclient import clean_local_ssh_key_entry
from launch_utils.startup_scripts import get_drc_startup_script,\
    get_open_vpn_single, create_openvpn_client_cfg_file, create_vpn_connect_file,\
    create_ros_connect_file, create_ssh_connect_file
from launch_utils.launch import LaunchException

from launch_utils.testing import get_boto_path, get_test_path, get_test_runner
from vpc_trio import OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP
from launch_utils.monitoring import LATENCY_TIME_BUFFER, record_ping_result,\
    machine_states
    



def aws_connect(credentials_ec2):    
    boto.config = BotoConfig(credentials_ec2)
    #boto.config = boto.pyami.config.Config(credentials_ec2)
    ec2conn = boto.connect_ec2()
    vpcconn =  boto.connect_vpc()    
    return ec2conn, vpcconn

def get_ping_data(ping_str):
    mini, avg, maxi, mdev  =  [float(x) for x in ping_str.split()[-2].split('/')]
    return (mini, avg, maxi, mdev)


def get_aws_states(ec2conn, machine_names_to_ids):

    aws_states = {}
    ids_to_machine_names = dict((v,k) for k,v in machine_names_to_ids.iteritems())
    
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for instance in instances:
        aws_is = instance.id
        if aws_is in ids_to_machine_names:
            state = instance.state
            machine = ids_to_machine_names[aws_is]
            aws_states[machine] = state
    return aws_states

def start_simulator(username, constellation, machine_name, package_name, launch_file_name, launch_args):

    constellation_dict = get_constellation_data(  constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_pair_name    = constellation_dict['sim_key_pair_name']
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    c = "bash cloudsim/start_sim.bash %s %s %s" %(package_name, launch_file_name, launch_args)
    cmd = c.strip()
    ssh_sim = SshClient(sim_machine_dir, sim_key_pair_name, 'ubuntu', sim_ip)
    r = ssh_sim.cmd(cmd)
    log('start_simulator %s' % r)


def stop_simulator(username, constellation, machine):
    
    constellation_dict = get_constellation_data( constellation)
    constellation_directory = constellation_dict['constellation_directory']
    sim_key_pair_name    = constellation_dict['sim_key_pair_name']
    sim_ip    = constellation_dict['simulation_ip']
    sim_machine_name = constellation_dict['sim_machine_name']
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    cmd = "bash cloudsim/stop_sim.bash"
    ssh_sim = SshClient(sim_machine_dir, sim_key_pair_name, 'ubuntu', sim_ip)
    r = ssh_sim.cmd(cmd)
    log('stop_simulator %s' % r)


def monitor(username, constellation_name, credentials_ec2, counter):
    _monitor(username, constellation_name, credentials_ec2, "simulator", counter)

def monitor_prerelease(username, constellation_name, credentials_ec2, counter):
    _monitor(username, constellation_name, credentials_ec2, "simulator_prerelease", counter)


def _monitor( username, 
             constellation_name, 
             credentials_ec2, 
             CONFIGURATION,  
             counter):
    
    time.sleep(1)
    constellation = ConstellationState( constellation_name)
    
    constellation_state = None
    try:
        
        constellation_state = constellation.get_value("constellation_state") 
        # log("constellation %s state %s" % (constellation_name, constellation_state) )
        if constellation_state == "terminated":
            log("constellation_state terminated for  %s " % constellation_name)
            return True
    except:
        log("Can't access constellation  %s data" % constellation_name)
        return True
    
    simulation_state = constellation.get_value('simulation_state')
    sim_machine_name = constellation.get_value('sim_machine_name')

    sim_state_index = machine_states.index(simulation_state)
    aws_ids = {}
    
    if constellation.has_value('simulation_aws_id'):
        aws_ids["sim"] = constellation.get_value('simulation_aws_id')

    if len(aws_ids):
        ec2conn = aws_connect(credentials_ec2)[0]
        aws_states = get_aws_states(ec2conn, aws_ids)
        constellation.set_value("simulation_aws_state", aws_states["sim"])

    if sim_state_index >= machine_states.index('packages_setup'):
        constellation_directory = constellation.get_value('constellation_directory')
        sim_key_pair_name = constellation.get_value('sim_key_pair_name')
        sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)

        sim_ip = constellation.get_value("simulation_ip")
        ssh_sim = SshClient(sim_machine_dir, sim_key_pair_name, 'ubuntu', sim_ip)

        if simulation_state == 'packages_setup':
            try:
                dpkg_line = ssh_sim.cmd("bash cloudsim/dpkg_log_sim.bash")
                simulation_package = parse_dpkg_line(dpkg_line)
                constellation.set_value('simulation_launch_msg', simulation_package)
            except Exception, e:
                log("monitor: cloudsim/dpkg_log_sim.bash error: %s" % e )

        o, ping_simulator = commands.getstatusoutput("ping -c3 %s" % sim_ip)
        if o == 0:
            sim_latency = constellation.get_value('simulation_latency')
            sim_latency = record_ping_result(sim_latency, ping_simulator, LATENCY_TIME_BUFFER)
            constellation.set_value('simulation_latency', sim_latency)
            
        if sim_state_index >= machine_states.index('running'):
            constellation.set_value('simulation_launch_msg', "complete")
            gl_state = constellation.get_value("simulation_glx_state")
            if gl_state == "running":
                try:
                    ping_gazebo = ssh_sim.cmd("bash cloudsim/ping_gazebo.bash")
                    log("cloudsim/ping_gazebo.bash = %s" % ping_gazebo )
                    constellation.set_value("gazebo", "running")
                except Exception, e:
                    log("monitor: cloudsim/ping_gazebo.bash error: %s" % e )
                    constellation.set_value("gazebo", "not running")
    #log("monitor not done")
    return False




def launch(username, constellation_name, tags, credentials_ec2, constellation_directory ):
    _launch(username, constellation_name, tags, credentials_ec2, constellation_directory,  "simulator", drc_package_name = "drcsim" )

def launch_prerelease(username, constellation_name, tags, credentials_ec2, constellation_directory):
    _launch(username, constellation_name, tags, credentials_ec2, constellation_directory,  "simulator_prerelease", drc_package_name = "drcsim-prerelease" )

def _launch(username, constellation_name, tags, credentials_ec2, constellation_directory, CONFIGURATION, drc_package_name):

    ec2conn = aws_connect(credentials_ec2)[0]
    constellation = ConstellationState( constellation_name)

    constellation.set_value('simulation_state', 'nothing')
    constellation.set_value('simulation_aws_state', 'nothing')
    constellation.set_value("gazebo", "not running")
    constellation.set_value('simulation_launch_msg', "starting")
    constellation.set_value('simulation_glx_state', "not running")
    constellation.set_value('sim_zip_file', 'not ready')
    constellation.set_value('simulation_latency','[]')
    
    constellation.set_value('username', username)
    sim_machine_name = "simulator_"+ constellation_name
    constellation.set_value('sim_machine_name', sim_machine_name)
    
    sim_machine_dir = os.path.join(constellation_directory, sim_machine_name)
    os.makedirs(sim_machine_dir)

    constellation.set_value('simulation_launch_msg', "setting up security groups")

    sim_sg_name = 'sim-sg-%s'%(constellation_name) 
    sim_security_group= ec2conn.create_security_group(sim_sg_name, "simulator security group for constellation %s" % constellation_name)
    sim_security_group.authorize('tcp', 80, 80, '0.0.0.0/0')     # web
    sim_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')     # ssh
    sim_security_group.authorize('icmp', -1, -1, '0.0.0.0/0')    # ping        
    sim_security_group.authorize('udp', 1194, 1194, '0.0.0.0/0') # OpenVPN

    sim_security_group_id = sim_security_group.id
    constellation.set_value('sim_security_group_id', sim_security_group_id)

    constellation.set_value('simulation_launch_msg', "creating ssh keys")

    sim_key_pair_name = 'key-sim-%s'%(constellation_name)
    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    key_pair = ec2conn.create_key_pair(sim_key_pair_name)
    key_pair.save(sim_machine_dir)

    roles_to_reservations ={}    

    SIM_AWS_TYPE = 'cg1.4xlarge'
    SIM_AWS_IMAGE= 'ami-98fa58f1'
    
    open_vpn_script = get_open_vpn_single(OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script, OPENVPN_SERVER_IP, drc_package_name)
    
    
    running_machines = {} 
    try:
        constellation.set_value('simulation_state', 'booting')
        constellation.set_value('simulation_launch_msg', "booting")
        
        # start a new machine, using the AWS api via the boto library
        res = ec2conn.run_instances( image_id       = SIM_AWS_IMAGE, 
                                     instance_type  = SIM_AWS_TYPE,
                                     #subnet_id      = subnet_id,
                                     #private_ip_address=SIM_IP,
                                     security_group_ids=[sim_security_group_id],
                                     key_name=sim_key_pair_name ,
                                     user_data=SIM_SCRIPT)
        
        roles_to_reservations['simulation_state'] = res.id
        

        
            # running_machines = wait_for_multiple_machines_to_run(ec2conn, roles_to_reservations, constellation, max_retries = 150, final_state = 'network_setup')
        count =200
        done = False
        color = "yellow"
        while not done:
            time.sleep(2)
            count -=1
            if count < 0:
                msg = "timeout while waiting for EC2 machine(s) %s" % sim_machine_name
                raise LaunchException(msg)
            
            for r in ec2conn.get_all_instances():
                if r.id ==  res.id:
                    state = r.instances[0].state
                    aws_id = r.instances[0].id 
                    log("%s aws %s state = %s" % (sim_machine_name, aws_id, state))
                    if  state == 'running':
                        running_machines['simulation_state'] = aws_id
                        constellation.set_value('simulation_state', 'network_setup')
                        constellation.set_value('simulation_launch_msg', 'network_setup')
                        
                        done = True
                    constellation.set_value('simulation_aws_state',state)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise                 
            
               
    
    
    simulation_aws_id =  running_machines['simulation_state']
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
    
    networking_done = get_ssh_cmd_generator(ssh_sim,"ls launch_stdout_stderr.log", "launch_stdout_stderr.log", constellation, "simulation_state", 'packages_setup' ,max_retries = 1000)
    #empty_ssh_queue([networking_done], sleep=2)
    
    color = "orange"
    for g in networking_done:
        time.sleep(1)
        launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, color, "waiting for network")
        if color == "yellow":
            color = "orange"
        else:
            color = "yellow"
            
    constellation.set_value('simulation_state', 'packages_setup')    
    constellation.set_value('simulation_launch_msg', "setting up scripts")
    launch_event(username, CONFIGURATION, constellation_name, sim_machine_name, color, "packages setup")
                
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
    
    ping_gl = """#!/bin/bash
    
    DISPLAY=localhost:0 timeout 10 glxinfo
    
    """ 
    ssh_sim.create_file(ping_gl, "cloudsim/ping_gl.bash")
    
    ping_gazebo = """#!/bin/bash
    
. /usr/share/drcsim/setup.sh
gztopic list
    
    """ 
    ssh_sim.create_file(ping_gazebo, "cloudsim/ping_gazebo.bash")
    

    hostname = sim_ip
    file_content = create_openvpn_client_cfg_file(hostname, client_ip = OPENVPN_CLIENT_IP, server_ip = OPENVPN_SERVER_IP)
    fname_vpn_cfg = os.path.join(sim_machine_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    
    fname_start_vpn = os.path.join(sim_machine_dir , "start_vpn.bash")    
    file_content = create_vpn_connect_file(OPENVPN_CLIENT_IP)
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)
    os.chmod(fname_start_vpn, 0755) # makes the file executable

    fname_ros = os.path.join(sim_machine_dir, "ros.bash")    
    file_content = create_ros_connect_file(OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP)

    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    key_filename = sim_key_pair_name + '.pem'
    fname_ssh_key =  os.path.join(sim_machine_dir, key_filename)
    os.chmod(fname_ssh_key, 0600)
    
    fname_ssh_sh =  os.path.join(sim_machine_dir,'ssh.bash')
    file_content = create_ssh_connect_file(key_filename, sim_ip)
    with open(fname_ssh_sh, 'w') as f:
            f.write(file_content)
    os.chmod(fname_ssh_sh, 0755) # makes the file executable
            
    fname_zip = os.path.join(sim_machine_dir, "%s.zip" % sim_machine_name)
    
    # wait (if necessary) for openvpn key to have been generated, then
    constellation.set_value('simulation_launch_msg',  "waiting for VPN key generation")
    remote_fname = "/etc/openvpn/static.key"
    sim_key_ready = get_ssh_cmd_generator(ssh_sim, "ls /etc/openvpn/static.key", "/etc/openvpn/static.key", constellation, "simulation_state", 'packages_setup' ,max_retries = 100)
    empty_ssh_queue([sim_key_ready], sleep=2)
    
    vpnkey_fname = os.path.join(sim_machine_dir, "openvpn.key")
    # download it locally for inclusion into the zip file
    
    constellation.set_value('simulation_launch_msg', "downloading sim key to CloudSim server") 
    ssh_sim.download_file(vpnkey_fname, remote_fname) 
    os.chmod(vpnkey_fname,0600)
    
    #creating zip
    files_to_zip = [ fname_ssh_key, 
                     fname_start_vpn,
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    constellation.set_value('simulation_launch_msg', "creating zip file bundle")    
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(sim_machine_name, short_fname)
            fzip.write(fname, zip_name)
    
    constellation.set_value('sim_zip_file', 'ready')
    
    constellation.set_value('simulation_launch_msg', "installing packages")
    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'booting' ,max_retries = 1500)
    empty_ssh_queue([sim_setup_done], sleep=2)
    
    constellation.set_value('simulation_state', "rebooting")
    constellation.set_value('simulation_launch_msg', "rebooting") 
    ssh_sim.cmd("sudo reboot")

    sim_setup_done = get_ssh_cmd_generator(ssh_sim, "ls cloudsim/setup/done", "cloudsim/setup/done", constellation, "simulation_state", 'running' ,max_retries = 300)
    empty_ssh_queue([sim_setup_done], sleep=2)

    constellation.set_value('simulation_glx_state', "running")
    
#    try:
#        ping_gl = ssh_sim.cmd("bash cloudsim/ping_gl.bash")
#        log("cloudsim/ping_gl.bash = %s" % ping_gl )
#        constellation.set_value('simulation_glx_state', "running")
#    except Exception, e:
#        constellation.set_value('error', "%s" % "OpenGL diagnostic failed")
#        raise        
    
    constellation.set_value('simulation_launch_msg', "reboot complete")
    constellation.set_value('simulation_state', "running")
    constellation.set_value('constellation_state', 'running')
    log("provisionning done")


def terminate(username, constellation_name, credentials_ec2, constellation_directory):
    _terminate(username, 'simulator', constellation_name, credentials_ec2, constellation_directory)
    
def terminate_prerelease(username, constellation_name, credentials_ec2, constellation_directory):
    _terminate(username, 'simulator_prerelease', constellation_name, credentials_ec2, constellation_directory)
    

def _terminate(username, CONFIGURATION, constellation_name, credentials_ec2, constellation_directory):

    resources = get_constellation_data( constellation_name)
    
    
    error_msg =""
    
    ec2conn = aws_connect(credentials_ec2)[0]
    constellation = ConstellationState( constellation_name)
    constellation.set_value('constellation_state', 'terminating')
    constellation.set_value('simulation_state', 'terminating')
    constellation.set_value('simulation_launch_msg', "terminating")
    
    log("terminate %s [user=%s, constellation_name=%s" % (CONFIGURATION, username, constellation_name) )
    
    try:
        running_machines =  {}
        running_machines['simulation_aws_state'] = resources['simulation_aws_id']
        
        wait_for_multiple_machines_to_terminate(ec2conn, 
                                                running_machines, 
                                                constellation, 
                                                max_retries = 150 )
        
        constellation.set_value('simulation_state', 'terminated')
        constellation.set_value('simulation_launch_msg', "terminated")
        print ('Waiting after killing instances...')
        time.sleep(10.0)
    except Exception, e:
        error_msg += "<b>Machine shutdown</b>: %s<br>" % e
        constellation.set_value('error', error_msg)        
        log ("error killing instances: %s" % e)
        
    try:
        sim_key_pair_name =  resources[ 'sim_key_pair_name']
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception, e:
        error_msg += "<b>Simulation key</b>: %s<br>" % e
        constellation.set_value('error', error_msg)        
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))
        
    try:    
        security_group_id =  resources['sim_security_group_id' ]
        ec2conn.delete_security_group(group_id = security_group_id)
    except Exception, e:
        error_msg += "<b>Simulator security group</b>: %s<br>" % e
        constellation.set_value('error', error_msg)        
        log("error cleaning up sim security group %s: %s" % (security_group_id, e))       
    
    constellation.set_value('constellation_state', 'terminated')
    

    

class SimulatorCase(unittest.TestCase):
    def atest(self):
        user = 'hugo@osrfoundation.org'
        const = 'cxdbcf5cf8'
        cred = get_boto_path()
        
        monitor(user, const, cred, 1)
        
    def atest_set_get(self):
        
        user_or_domain = "hugo@toto.com"
        constellation = "constellation"
        value = {'a':1, 'b':2}
        expiration = 25
        set_constellation_data( constellation, value, expiration)
        
        data = get_constellation_data(constellation)
        self.assert_(data['a'] == value['a'], "not set")

class TrioCase(unittest.TestCase):
    
    def test_launch(self):
        CONFIGURATION = 'simulator'
        test_name = "test_" + CONFIGURATION
        self.constellation_name =  get_unique_short_name(test_name + "_")
        
        self.username = "toto@osrfoundation.org"
        self.credentials_ec2  = get_boto_path()
        
        self.tags = {'TestCase':CONFIGURATION, 'configuration': CONFIGURATION, 'constellation' : self.constellation_name, 'user': self.username, 'GMT':"now"}
        
        self.constellation_directory = os.path.abspath( os.path.join(get_test_path(test_name), self.constellation_name))
        print("creating: %s" % self.constellation_directory )
        os.makedirs(self.constellation_directory)
        
        launch(self.username, self.constellation_name, self.tags, self.credentials_ec2, self.constellation_directory)
                
        sweep_count = 10
        for i in range(sweep_count):
            print("monitoring %s/%s" % (i,sweep_count) )
            monitor(self.username, self.constellation_name, self.credentials_ec2, i)
            time.sleep(1)
    
        #ToDo: Loop 
        
        #ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -i /home/caguero/workspace/cloudsim/test-reports/test_simulator/test_simulator_6fe051aa/simulator_test_simulator_6fe051aa/key-sim-test_simulator_6fe051aa.pem ubuntu@67.202.40.198 bash cloudsim/ping_gazebo.bash

    
    
    def tearDown(self):
        unittest.TestCase.tearDown(self)
        #self.machine.terminate() 
        # self.constellation_name = 
        terminate(self.username, self.constellation_name, self.credentials_ec2, self.constellation_directory)
        
        
        
if __name__ == "__main__":
    xmlTestRunner = get_test_runner()   
    unittest.main(testRunner = xmlTestRunner)       