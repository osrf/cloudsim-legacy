from __future__ import with_statement
from __future__ import print_function

import os
import uuid
import unittest
import zipfile
import tempfile
import shutil



from common import StdoutPublisher, INSTALL_VPN, Machine,\
    clean_local_ssh_key_entry, MachineDb, get_test_runner, testing
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

apt-get install -y unzip zip
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
    import redis
    redis_client = redis.Redis()
    print(msg)
    redis_client.publish("launchers", msg)
    

    

    
def launch(username, constellation_name, tags, publisher, credentials_ec2, constellation_directory, website_distribution = TEAM_LOGIN_DISTRIBUTION):
    
    
    log("cloudsim launch constellation '%s'" % constellation_name)
    machine_name = "cloudsim_" +constellation_name
    
    
    startup_script = """#!/bin/bash
# Exit on error
set -e

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list", file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'

    startup_script += TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE
    # log(startup_script)
 
    
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

    machine = Machine(machine_name,
                     config,
                     publisher.event,
                     tags,
                     credentials_ec2,
                     constellation_directory)
                     
    
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

    log("Waiting for ssh connection")
    machine.ssh_wait_for_ready("/home/ubuntu")
    
    log("Waiting for setup to complete")
    machine.ssh_wait_for_ready()
    log("   setup to complete")

    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/%s/%s" % (machine.config.username, short_file_name)
    log("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )
    out = machine.scp_send_file(website_distribution, remote_fname)
    log ("\t%s"% out)
    machine.ssh_wait_for_ready(remote_fname)
    
    
    log("unzip web app")
    out = machine.ssh_send_command("unzip " + remote_fname )
    log ("\t%s"% out)
    
    log("Setup admin user %s" % username)
    add_user_cmd = 'echo \'{"%s":"admin"}\' > cloudsim/distfiles/users' % username 
    log("add user to cloudsim: %s" % add_user_cmd)
    out =machine.ssh_send_command(add_user_cmd)
    log ("\t%s"% out)
    
    log("Uploading the key file to the server")
    remote_fname = "/home/%s/cloudsim/cloudsim_ssh.zip" % (machine.config.username)
    log("uploading '%s' to the server to '%s'" % (fname_zip, remote_fname) )
    out = machine.scp_send_file(fname_zip , remote_fname)
    log ("\t%s"% out)
    
    log("Uploading the ec2 credentials to the server")
    remote_fname = "/home/%s/cloudsim/boto-useast" % (machine.config.username)
    log("uploading '%s' to the server to '%s'" % (credentials_ec2, remote_fname) )
    out = machine.scp_send_file(credentials_ec2 , remote_fname)
    log ("\t%s"% out)


    
    #out =machine.ssh_send_command('echo %s > cloudsim/distfiles/users' % username)
    log("Deploying the cloudsim web app")
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
    
    return machine
    
        
def cloudsim_bootstrap(username, ec2):
    print(__file__)
    constellation_name = str(uuid.uuid1())
    tags = {}
    constellation_directory = tempfile.mkdtemp("cloudsim")
    
    zip_path = zip_cloudsim()
    pub = StdoutPublisher()
    launch(username, constellation_name, tags, pub, ec2, constellation_directory, zip_path)

def zip_cloudsim():
    
    tmp_dir = tempfile.mkdtemp("cloudsim")
    tmp_zip = os.path.join(tmp_dir, "cloudsim.zip")
    full_path_of_cloudsim = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # Account for having a version in the name of the directory, which we
    # want to get rid of
    shutil.copytree(full_path_of_cloudsim, os.path.join(tmp_dir, 'cloudsim'))
    os.chdir(tmp_dir)
    o = commands.getoutput('zip -r %s cloudsim'%(tmp_zip))
  
    return tmp_zip
    
    
class TestCases(unittest.TestCase):
    
   
    
#    def test_launch(self):
#        
#        username = "hugo@osrfoundation.org"
#        machine_name = "microvpn_" + str(uuid.uuid1())
#        publisher = StdoutPublisher()
#        ec2 = "/home/hugo/code/boto.ini"
#        root_directory = '../launch_test'
#        uid = uuid.uuid1()
#        machine_name = "cloudsim_" + str( uid )
#        tags = {}
#        tags['type'] = 'TeamLogin'
#        tags['machine'] = machine_name
#        tags['user'] = username
#        tags['origin'] = 'test_launch test case'
#        launch(username, machine_name, tags, publisher, ec2, root_directory)


    def test_cloudsim_strap(self):
        
        #    
        zip_path = zip_cloudsim()
        self.assert_(os.path.exists(zip_path), "no zip done!")
        
    def test_cloudsim(self):
        ec2 = "/home/hugo/code/boto.ini"
        cloudsim_bootstrap("gerkey@osrfoundationp.org", ec2)
        
        
if __name__ == "__main__":
    
    unittest.main() #(testRunner = testing.get_test_runner())
    
    print(sys.argv)
    
    
     
