from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile

from common import StdoutPublisher, INSTALL_VPN, Machine2,\
    clean_local_ssh_key_entry, MachineDb
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
import time
import commands
from common.startup_script_builder import SOURCES_LIST_PRECISE

TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE = """#!/bin/bash

echo "In the beginning was the Computer" > /home/ubuntu/setup.log

# Exit on error
set -e
echo "config: exit on error" >> /home/ubuntu/setup.log

#echo "waiting for network" >> /home/ubuntu/setup.log
#while true; do if ping -w 1 security.ubuntu.com; then break; else sleep 1; fi; done
#echo "security.ubuntu.com ping success" >> /home/ubuntu/setup.log


# Overwrite the sources.list file with different content
cat <<DELIM > /etc/apt/sources.list
%s
DELIM
echo "sources.list overriden" >> /home/ubuntu/setup.log


apt-get update
echo "SYSTEM UPDATED" >> /home/ubuntu/setup.log

echo "Installing packages" >> /home/ubuntu/setup.log

apt-get install -y unzip
echo "unzip installed" >> /home/ubuntu/setup.log

# install mercurial and fetch latest version of the Team Login website
apt-get install -y mercurial
echo "mercurial installed" >> /home/ubuntu/setup.log

apt-get install -y cloud-utils
echo "cloud-utils installed" >> /home/ubuntu/setup.log

apt-get install -y apache2
echo "apache2 installed" >> /home/ubuntu/setup.log

# apt-get install -y libapache2-mod-python
# echo "apache2 with mod-python installed" >> /home/ubuntu/setup.log

apt-get install -y redis-server python-pip
sudo pip install redis
echo "redis installed" >> /home/ubuntu/setup.log
 
apt-add-repository -y ppa:rye/ppa
apt-get update
echo "ppa:rye/ppa repository added" >> /home/ubuntu/setup.log

apt-get install -y libapache2-mod-auth-openid
ln -s /etc/apache2/mods-available/authopenid.load /etc/apache2/mods-enabled
echo "libapache2-mod-auth-openid 0.6 installed from ppa:rye/ppa" >> /home/ubuntu/setup.log

/etc/init.d/apache2 restart
echo "apache2 restarted" >> /home/ubuntu/setup.log

# to list installed modules  
# apachectl -t -D DUMP_MODULES

# Make sure that www-data can run programs in the background (used inside CGI scripts)
echo www-data > /etc/at.allow



echo "STARTUP COMPLETE" >> /home/ubuntu/setup.log



"""


    
def launch(username, machine_name, tags, publisher, credentials_ec2, root_directory):

    print("create distribution")    
    path = os.path.split(__file__)[0]
    cloudsim_path = path = os.path.join(path, '..','..')
    cmd_path = os.path.join(cloudsim_path,'distfiles', 'make_zip.bash')
    website_distribution = os.path.join(cloudsim_path,'..', 'cloudsim.zip') # outside cloudsim
    o = commands.getoutput(cmd_path)
    print(o)
     
    startup_script = """#!/bin/bash
# Exit on error
set -e

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list",file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'

    startup_script += TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE
    print(startup_script)

    config = Machine_configuration()
    config.initialize(   image_id ="ami-137bcf7a", 
                         instance_type = 't1.micro', # 'm1.small' , 
                         security_groups = ['team_login'],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=200)

    machine = Machine2(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     root_directory)
                     
    
    machine.create_ssh_connect_script()
    clean_local_ssh_key_entry(machine.config.ip )
    print("")
    print("")
    print("Waiting for ssh")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    print("Waiting for setup to complete")
    machine.ssh_wait_for_ready()

    
    print("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )
    machine.scp_send_file(website_distribution, remote_fname)
    
    #checking that the file is there
    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/%s/%s" % (team_login.config.username, short_file_name)
    machine.ssh_send_command("ls " + remote_fname )
    
    print("unzip web app")
    out = machine.ssh_send_command("unzip " + remote_fname )
    print ("\t%s"% out)
    
    print("running deploy script '%s' remotely" % deploy_script_fname)
    out = machine.ssh_send_command("bash " + deploy_script_fname  )
    print ("\t%s"% out)
    print('setup complete')
    print("%s\n"%(machine.user_ssh_command()))
    print("http://%s"% team_login.config.hostname)
            

class TestCases(unittest.TestCase):
    
   
    
    def test_micro(self):
        
        username = "toto@toto.com"
        machine_name = "microvpn_" + str(uuid.uuid1())
        publisher = StdoutPublisher()
        ec2 = "../../../boto.ini"
        root_directory = '../launch_test'
        uid = uuid.uuid1()
        machine_name = "team_login_" + str( uid )
        tags = {}
        tags['type'] = 'team_login'
#        
        launch(username, machine_name, tags, publisher, ec2, root_directory)
#        
        

if __name__ == "__main__":
    unittest.main()            