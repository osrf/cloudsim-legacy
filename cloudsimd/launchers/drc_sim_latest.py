from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile
import time


from common import StdoutPublisher, INSTALL_VPN, Machine,\
    clean_local_ssh_key_entry, MachineDb, get_test_runner, constants
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
from common.startup_script_builder import  ROS_SETUP_STARTUP_SCRIPT,\
    create_xorg_config_file, SOURCES_LIST_PRECISE, XGL_STARTUP_BEFORE,\
    XGL_STARTUP_AFTER, LAUNCH_SCRIPT_HEADER, get_monitoring_tools_script
from common.machine import set_machine_tag, create_ec2_proxy,\
    get_unique_short_name,\
    create_if_not_exists_simulator_security_group



def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)

DRC_SETUP = """

echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | sudo apt-key add -

echo "package update" >> /home/ubuntu/setup.log
apt-get update

echo "install drc" >> /home/ubuntu/setup.log
apt-get install -y drcsim

echo "install cloudsim-client-tools" >> /home/ubuntu/setup.log
apt-get install -y cloudsim-client-tools

echo "source drc setup from bashrc" >> /home/ubuntu/setup.log
echo 'source /usr/share/drcsim/setup.sh' >> ~/.bashrc

"""


def get_launch_script(boundary_creds):
    startup_script = LAUNCH_SCRIPT_HEADER
    
    startup_script += 'date > /home/ubuntu/setup.log\n'
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list",file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'
    startup_script += 'date > /home/ubuntu/setup.log\n'

    startup_script += 'echo "setup VPN" >> /home/ubuntu/setup.log\n'
    
    #file_content = create_openvpn_server_cfg_file()
    file_content = create_openvpn_server_cfg_file(client_ip = constants.OV_SIM_CLIENT_IP, server_ip = constants.OV_SIM_SERVER_IP)
    startup_script += inject_file_into_script("openvpn.config",file_content)
    startup_script += INSTALL_VPN
    
    startup_script += 'echo "setup X and gl" >> /home/ubuntu/setup.log\n'
    startup_script += XGL_STARTUP_BEFORE
    
    startup_script += 'echo "create xorg.conf" >> /home/ubuntu/setup.log\n'
    file_content = create_xorg_config_file()
    startup_script += inject_file_into_script("/etc/X11/xorg.conf",file_content)
    
    startup_script += XGL_STARTUP_AFTER
    
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    startup_script += 'echo "setting drc / ros  package repo" >> /home/ubuntu/setup.log\n'
    startup_script += DRC_SETUP
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    
#    startup_script += 'date >> /home/ubuntu/setup.log\n'
#    startup_script += get_monitoring_tools_script(boundary_creds) # ("GxVCMUXvbNINCOV1XFtYPLvcC9r:3CTxnYc1eLQeZKjAavWX0wjMDBu")
#    startup_script += 'date >> /home/ubuntu/setup.log\n'
    
    startup_script += 'echo "Setup complete" >> /home/ubuntu/setup.log\n'
    startup_script += 'date >> /home/ubuntu/setup.log\n'
    return startup_script
    

def launch(username, constellation_name, tags, credentials_ec2, root_directory, machine_name_param = None,):
    
    machine_name = machine_name_param
    if not machine_name:
        machine_name = "simulator_" +constellation_name
    
    security_group = "drc_sim_latest"
    ec2 = create_ec2_proxy(credentials_ec2)
    create_if_not_exists_simulator_security_group(ec2, security_group, "DRC simulator: ping, ssh and vpn")
    
    boundary_creds = None
    #if username.find('@osrfoundation.org') > 0:
    #    boundary_creds = "GxVCMUXvbNINCOV1XFtYPLvcC9r:3CTxnYc1eLQeZKjAavWX0wjMDBu"
    startup_script = get_launch_script(boundary_creds)
        
    config = Machine_configuration()
    config.initialize(   image_id = "ami-98fa58f1",  
                         instance_type = 'cg1.4xlarge', # 'm1.small' , 
                         security_groups = [security_group],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=1500)
    
    domain = username.split("@")[1]
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "waiting for ip")
    set_machine_tag(domain, constellation_name, machine_name, "up", True)
    
    machine = Machine(username,
                      machine_name,
                     config,
                     tags,
                     credentials_ec2,
                     root_directory)

    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "booting up")
    machine.create_ssh_connect_script()
    clean_local_ssh_key_entry(machine.config.ip )

    log("%s/%s> Waiting for ssh" % (constellation_name, machine_name) )
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    log("%s/%s> write openvpn.config" % (constellation_name, machine_name))
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "preparing keys")
    file_content = create_openvpn_client_cfg_file(machine.config.hostname, client_ip = constants.OV_SIM_CLIENT_IP, server_ip = constants.OV_SIM_SERVER_IP)
    fname_vpn_cfg = os.path.join(machine.config.cfg_dir, "openvpn.config")
    with open(fname_vpn_cfg, 'w') as f:
        f.write(file_content)
    
    log("%s/%s> write start_vpn.sh" % (constellation_name, machine_name))
    fname_start_vpn = os.path.join(machine.config.cfg_dir, "start_vpn.sh")    
    file_content = create_vpn_connect_file()
    with open(fname_start_vpn, 'w') as f:
        f.write(file_content)

    log("%s/%s> write ros.sh" % (constellation_name, machine_name))
    fname_ros = os.path.join(machine.config.cfg_dir, "ros.sh")    
    file_content = create_ros_connect_file()
    with open(fname_ros, 'w') as f:
        f.write(file_content)
    
    fname_ssh_key =  os.path.join(machine.config.cfg_dir, machine.config.kp_name + '.pem')
    fname_ssh_sh =  os.path.join(machine.config.cfg_dir,'ssh.sh')
    
    fname_zip = os.path.join(machine.config.cfg_dir, "%s.zip" % machine.config.uid)
    
    # wait (if necessary) for openvpn key to have been generated, then
    # download it locally for inclusion into the zip file
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "waiting for openvpn key setup")
    remote_fname = "/etc/openvpn/static.key"
    log("%s/%s> waiting for %s" % (constellation_name, machine_name, remote_fname) ) 
    machine.ssh_wait_for_ready(remote_fname)
    
    vpnkey_fname = os.path.join(machine.config.cfg_dir, "openvpn.key")
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "openvpn key download")
    log("%s/%s> Downloading VPN key remote %s to %s" % (constellation_name, machine_name, remote_fname, vpnkey_fname))
    machine.scp_download_file(vpnkey_fname, remote_fname)

    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "creating keys zip file")
    log("%s/%s> creating %s" % (constellation_name, machine_name, fname_zip))
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh, 
                     fname_vpn_cfg,
                     vpnkey_fname,
                     fname_ros,]
    
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(machine.config.uid, short_fname)
            fzip.write(fname, zip_name)
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "installing packages")
    log("%s/%s> Waiting for setup to complete" % (constellation_name, machine_name) )
    # machine.ssh_wait_for_ready()
    
    setup_files = ["/usr/share/doc/gnome-session/copyright",
                   "/usr/share/doc/ros-fuerte-ros/copyright", 
                   "/opt/ros/fuerte/share/urdfdom_model", 
                   "/usr/share/doc/gazebo/copyright", 
                   "/usr/share/doc/drcsim/copyright", 
                   "/usr/share/doc/cloudsim-client-tools/copyright"]
    for f in setup_files:
        machine.ssh_wait_for_ready(f)
    
    # wait for setup complete
    machine.ssh_wait_for_ready()
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "rebooting")
    log("%s/%s> rebooting machine" % (constellation_name, machine_name))
    machine.reboot()
    
    log("%s/%s> waiting for machine to be up again" % (constellation_name, machine_name))
    # machine.get_aws_status(timeout)['state'] == 'running'
    machine.ssh_wait_for_ready("/home/ubuntu")
    log("%s/%s> machine ready"% (constellation_name, machine_name))
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "running")
 

class Test_launch_drcim_latest(unittest.TestCase):
    
    def atest_launch(self):
        from common.testing import get_test_path, get_boto_path
        username = "test@osrfoundation.org" 
        constellation_name = "test_launch_drcim_latest_" + get_unique_short_name('test')
        tags = {"test":"test_launch_drcim_latest"} 
        
        publisher = StdoutPublisher()
        root_directory = get_test_path('Test_launch_drcim_latest')
        machine = launch(username, constellation_name, tags, publisher, get_boto_path(), root_directory)
        
        machine.terminate()
        
if __name__ == "__main__":
    from common.testing import get_test_runner
    unittest.main(testRunner =  get_test_runner())               