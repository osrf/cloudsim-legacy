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
from common import SOURCES_LIST_PRECISE, get_boto_path

from common import TEAM_LOGIN_DISTRIBUTION
from common.machine import set_machine_tag, create_ec2_proxy,\
    create_if_not_exists_web_app_security_group, get_unique_short_name
from common import kill_all_ec2_instances
from common.startup_script_builder import LAUNCH_SCRIPT_HEADER,\
    get_monitoring_tools_script
import redis
import json

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

"""

#old_print = print
#print = log

def log(msg):
    try:
        import redis
        redis_client = redis.Redis()
        redis_client.publish("launchers", msg)
    except:
        print("Warning: redis not installed.")
    print("cloudsim log> %s" % msg)



def launch(username, constellation_name, tags,  credentials_ec2, constellation_directory, machine_name_param = None):
    website_distribution = TEAM_LOGIN_DISTRIBUTION
    do_launch(username, constellation_name, tags,  credentials_ec2, constellation_directory, machine_name_param, website_distribution)  
    
def do_launch(username, constellation_name, tags,  credentials_ec2, constellation_directory, machine_name_param, website_distribution):

    machine_name = machine_name_param
    if not machine_name:
        machine_name = "cloudsim_" +constellation_name

    # log(startup_script)
    security_group = "cloudsim"
    ec2 = create_ec2_proxy(credentials_ec2)
    create_if_not_exists_web_app_security_group(ec2, security_group, "web server and ssh")

    log("cloudsim launch constellation '%s'" % constellation_name)
    
        
        
    startup_script = LAUNCH_SCRIPT_HEADER
    
    
    startup_script += """

echo "Creating openvpn.conf" >> /home/ubuntu/setup.log

"""
    
    file_content = SOURCES_LIST_PRECISE
    startup_script += 'echo "creating sources.list" >> /home/ubuntu/setup.log\n'
    startup_script += inject_file_into_script("/etc/apt/sources.list", file_content)
    startup_script += 'echo "package update" >> /home/ubuntu/setup.log\n'
    startup_script += 'apt-get update\n'

    startup_script += TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE
    
    startup_script +=get_monitoring_tools_script("GxVCMUXvbNINCOV1XFtYPLvcC9r:3CTxnYc1eLQeZKjAavWX0wjMDBu")

    startup_script += """
echo "STARTUP COMPLETE" >> /home/ubuntu/setup.log

"""

    config = Machine_configuration()
    config.initialize(   image_id ="ami-137bcf7a", 
                         # instance_type = 'm1.small',  
                         instance_type = 't1.micro', 
                         security_groups = [security_group],
                         username = 'ubuntu', 
                         distro = 'precise',
                         startup_script = startup_script,
                         ip_retries=100, 
                         ssh_retries=200)

    machine = Machine(username,
                      machine_name,
                      config,
                      tags,
                      credentials_ec2,
                      constellation_directory)
                     
    domain = username.split("@")[1]
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "waiting for ip")
    set_machine_tag(domain, constellation_name, machine_name, "up", True)
    
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
    
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "installing packages")
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
    log("%s\n"%(machine.get_user_ssh_command_string()))
    log("http://%s"% machine.config.hostname)
    set_machine_tag(domain, constellation_name, machine_name, "launch_state", "running")
 
    
    
def cloudsim_bootstrap(username, ec2):
    print(__file__)
    constellation_name = get_unique_short_name('test_')
    tags = {}
    constellation_directory = tempfile.mkdtemp("cloudsim")
    
    zip_path = zip_cloudsim()
    machine = do_launch(username, constellation_name, tags,  ec2, constellation_directory, None, zip_path)
    return machine

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
    
    
class CloudsimBootStrapTestCase(unittest.TestCase):
    
    def tearDown(self):
        print("Killing all instances")
        ec2 = create_ec2_proxy(get_boto_path())
        kill_all_ec2_instances(ec2)

    def test_cloudsim_zip(self):
        zip_path = zip_cloudsim()
        self.assert_(os.path.exists(zip_path), "no zip done!")
        
    def test_cloudsim(self):
        
        ec2 = get_boto_path()
        machine = cloudsim_bootstrap("test@osrfoundation.org", ec2)
        
        machine.ssh_wait_for_ready("/home/ubuntu/cloudsim")
        self.assert_(1==1, "machine ready")
        
        self.assert_(machine.ping(10), "can't reach")
        machine.terminate()
        
        
if __name__ == "__main__":
    
    unittest.main(testRunner = get_test_runner())
    
    
