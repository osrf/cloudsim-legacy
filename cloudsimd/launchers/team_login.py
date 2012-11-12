from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile
import redis
redis_client = redis.Redis()


from common import StdoutPublisher, INSTALL_VPN, Machine2,\
    clean_local_ssh_key_entry, MachineDb, get_test_runner
from common import create_openvpn_server_cfg_file,\
    inject_file_into_script, create_openvpn_client_cfg_file,\
    create_ros_connect_file, create_vpn_connect_file
from common import Machine_configuration
import time
import commands
from common import SOURCES_LIST_PRECISE

from common import TEAM_LOGIN_DISTRIBUTION

TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE = """

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

sudo pip install unittest-xml-reporting
echo "XmlTestRunner installed" >> /home/ubuntu/setup.log

 
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
#old_print = print
#print = log

def log(msg):
    print(msg)
    redis_client.publish("launchers", msg)
    

    
def launch(username, machine_name, tags, publisher, credentials_ec2, root_directory):

#    log("create distribution")    
#    path = os.path.split(__file__)[0]
#    cloudsim_path = path = os.path.join(path, '..','..')
#    cmd_path = os.path.join(cloudsim_path,'distfiles', 'make_zip.bash')
#    website_distribution =os.path.abspath( os.path.join(cloudsim_path,'..', 'cloudsim.zip') ) # outside cloudsim
#    o = commands.getoutput(cmd_path)
#    log(o)
    
    website_distribution = TEAM_LOGIN_DISTRIBUTION
    
     
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
    log(startup_script)
 

    config = Machine_configuration()
    config.initialize(   image_id ="ami-137bcf7a", 
                         # instance_type = 'm1.small',  
                         instance_type = 't1.micro', 
                         security_groups = ['TeamLogin'],
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
    fname_ssh_key =  os.path.join(machine.config.cfg_dir, machine.config.kp_name + '.pem')
    fname_ssh_sh =  os.path.join(machine.config.cfg_dir,'ssh.sh')
    fname_zip = os.path.join(machine.config.cfg_dir, "%s.zip" % machine.config.uid)
    
    files_to_zip = [ fname_ssh_key, 
                     fname_ssh_sh, 
                   ]
    
    log("creating %s" % fname_zip)
    with zipfile.ZipFile(fname_zip, 'w') as fzip:
        for fname in files_to_zip:
            short_fname = os.path.split(fname)[1]
            zip_name = os.path.join(machine.config.uid, short_fname)
            fzip.write(fname, zip_name)        
    
    
    clean_local_ssh_key_entry(machine.config.ip )

    log("Waiting for /home/ubuntu")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    log("Waiting for setup to complete")
    machine.ssh_wait_for_ready()
    log("   setup to complete")
    #checking that the file is there
    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/%s/%s" % (machine.config.username, short_file_name)
    # machine.ssh_send_command("ls " + remote_fname )

    log("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )
    out = machine.scp_send_file(website_distribution, remote_fname)
    log ("\t%s"% out)
    machine.ssh_wait_for_ready(remote_fname)
    
    log("unzip web app")
    out = machine.ssh_send_command("unzip " + remote_fname )
    log ("\t%s"% out)
    
    log("add user to cloudsim")
    out =machine.ssh_send_command("echo %s > cloudsim/distfiles/users" % username)
    log ("\t%s"% out)
    
    deploy_script_fname = "/home/%s/cloudsim/deploy.sh" % machine.config.username 
    log("running deploy script '%s' remotely" % deploy_script_fname)
    out = machine.ssh_send_command("bash " + deploy_script_fname  )
    log ("\t%s"% out)
    
    
    
#    print("check that file is there")
#    out = machine.ssh_wait_for_ready('/var/www-cloudsim-auth/users')
#    print ("\t%s"% out)
    
    log('setup complete')
    log("%s\n"%(machine.user_ssh_command()))
    log("http://%s"% machine.config.hostname)
    
        

class TestCases(unittest.TestCase):
    
   
    
    def test_launch(self):
        
        username = "hugo@osrfoundation.org"
        machine_name = "microvpn_" + str(uuid.uuid1())
        publisher = StdoutPublisher()
        ec2 = "/home/hugo/code/boto.ini"
        root_directory = '../launch_test'
        uid = uuid.uuid1()
        machine_name = "team_login_" + str( uid )
        tags = {}
        tags['type'] = 'TeamLogin'
        tags['machine'] = machine_name
        tags['user'] = username
        tags['origin'] = 'test_launch test case'
        launch(username, machine_name, tags, publisher, ec2, root_directory)
#        
        

if __name__ == "__main__":
    unittest.main(testRunner = get_runner()) 