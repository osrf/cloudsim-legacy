from __future__ import with_statement
from __future__ import print_function

import os
import sys

from common import Machine2, Machine_configuration
import uuid
from common import StdoutPublisher

TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE = """#!/bin/bash

echo "In the beginning was the Computer" > /home/ubuntu/STARTUP_SCRIPT_LOG

# Exit on error
set -e
echo "config: exit on error" >> /home/ubuntu/STARTUP_SCRIPT_LOG

#echo "waiting for network" >> /home/ubuntu/STARTUP_SCRIPT_LOG
#while true; do if ping -w 1 security.ubuntu.com; then break; else sleep 1; fi; done
#echo "security.ubuntu.com ping success" >> /home/ubuntu/STARTUP_SCRIPT_LOG


# Overwrite the sources.list file with different content
cat <<DELIM > /etc/apt/sources.list
%s
DELIM
echo "sources.list overriden" >> /home/ubuntu/STARTUP_SCRIPT_LOG


apt-get update
echo "SYSTEM UPDATED" >> /home/ubuntu/STARTUP_SCRIPT_LOG

echo "Installing packages" >> /home/ubuntu/STARTUP_SCRIPT_LOG

apt-get install -y unzip
echo "unzip installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# install mercurial and fetch latest version of the Team Login website
apt-get install -y mercurial
echo "mercurial installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

apt-get install -y cloud-utils
echo "cloud-utils installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

apt-get install -y apache2
echo "apache2 installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# apt-get install -y libapache2-mod-python
# echo "apache2 with mod-python installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

apt-get install -y redis-server python-pip
sudo pip install redis
echo "redis installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG
 
apt-add-repository -y ppa:rye/ppa
apt-get update
echo "ppa:rye/ppa repository added" >> /home/ubuntu/STARTUP_SCRIPT_LOG

apt-get install -y libapache2-mod-auth-openid
ln -s /etc/apache2/mods-available/authopenid.load /etc/apache2/mods-enabled
echo "libapache2-mod-auth-openid 0.6 installed from ppa:rye/ppa" >> /home/ubuntu/STARTUP_SCRIPT_LOG

/etc/init.d/apache2 restart
echo "apache2 restarted" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# to list installed modules  
# apachectl -t -D DUMP_MODULES

# Make sure that www-data can run programs in the background (used inside CGI scripts)
echo www-data > /etc/at.allow



echo "STARTUP COMPLETE" >> /home/ubuntu/STARTUP_SCRIPT_LOG



"""


SOURCES_LIST = """
## Note, this file is written by cloud-init on first boot of an instance
## modifications made here will not survive a re-bundle.
## if you wish to make changes you can:
## a.) add 'apt_preserve_sources_list: true' to /etc/cloud/cloud.cfg
##     or do the same in user-data
## b.) add sources in /etc/apt/sources.list.d
## c.) make changes to template file /etc/cloud/templates/sources.list.tmpl
#

# See http://help.ubuntu.com/community/UpgradeNotes for how to upgrade to
# newer versions of the distribution.
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise main restricted
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise main restricted

## Major bug fix updates produced after the final release of the
## distribution.
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates main restricted
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates main restricted

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu
## team. Also, please note that software in universe WILL NOT receive any
## review or updates from the Ubuntu security team.
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise universe
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise universe
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates universe
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates universe

## N.B. software from this repository is ENTIRELY UNSUPPORTED by the Ubuntu 
## team, and may not be under a free licence. Please satisfy yourself as to
## your rights to use the software. Also, please note that software in 
## multiverse WILL NOT receive any review or updates from the Ubuntu
## security team.
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise multiverse
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise multiverse
deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates multiverse
deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates multiverse

## Uncomment the following two lines to add software from the 'backports'
## repository.
## N.B. software from this repository may not have been tested as
## extensively as that contained in the main release, although it includes
## newer versions of some applications which may provide useful features.
## Also, please note that software in backports WILL NOT receive any review
## or updates from the Ubuntu security team.
# deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse
# deb-src http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-backports main restricted universe multiverse

## Uncomment the following two lines to add software from Canonical's
## 'partner' repository.
## This software is not part of Ubuntu, but is offered by Canonical and the
## respective vendors as a service to Ubuntu users.
# deb http://archive.canonical.com/ubuntu precise partner
# deb-src http://archive.canonical.com/ubuntu precise partner

deb http://security.ubuntu.com/ubuntu precise-security main restricted
deb-src http://security.ubuntu.com/ubuntu precise-security main restricted
deb http://security.ubuntu.com/ubuntu precise-security universe
deb-src http://security.ubuntu.com/ubuntu precise-security universe
deb http://security.ubuntu.com/ubuntu precise-security multiverse
deb-src http://security.ubuntu.com/ubuntu precise-security multiverse

"""

def generate_setup_script(distro):
    startup_script = TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE % (SOURCES_LIST)
    return startup_script


if __name__ == '__main__':
    
    root_directory = "team_login_pem"
    distro = "precise"

    print ("create_team_login_instance\n")
    
    if(len(sys.argv) < 3 ):
        print("usage:\npython %s boto_file website_distribution" % os.path.split(sys.argv[0])[1])
        exit(0)
    
    credentials_ec2 = sys.argv[1]       # "boto.cfg"
    website_distribution = sys.argv[2]  # "cloudsim.zip"
    
    
    
    print("credentials_ec2: %s" % credentials_ec2)
    print("website_distribution: %s" % website_distribution)
    print("")
    
#    team_login =  Machine2(credentials_ec2 = credentials_ec2,
#            pem_key_directory = "team_login_pem", 
#            image_id = "ami-137bcf7a",
#            instance_type= "m1.small", # "t1.micro"
#            security_groups = ["TeamLogin"],
#            username = "ubuntu", 
#            distro = "precise")
    
    startup_script = generate_setup_script(distro)
    
    config = Machine_configuration()        
    config.initialize(  image_id ="ami-137bcf7a", 
                        instance_type= "t1.micro", # "m1.small"
                        security_groups = ["TeamLogin"],
                        username = "ubuntu",
                        distro = distro,  
                        startup_script = startup_script,
                        ip_retries = 200,
                        ssh_retries = 200
                        )
    
    deploy_script_fname = "/home/%s/cloudsim/deploy.sh" % config.username 
    remote_fname = '/home/%s' % (config.username)
    
    machine_name = "team_" + str(uuid.uuid1())
    publisher = StdoutPublisher()
    tags = {'type': 'team login machine',
            'version': 'n/a',
            'distribution' : website_distribution}
    
    team_login  = Machine2(machine_name, 
                           config, 
                           publisher.event, 
                           tags, 
                           credentials_ec2,
                           root_directory =  root_directory)
    
    print("\n%s"%(team_login.config.hostname))
    print("%s\n\n"%(team_login.user_ssh_command()))
    print("Waiting for ssh")
    team_login.ssh_wait_for_ready()
    
    
    print("uploading '%s' to the server to '%s'" % (website_distribution, remote_fname) )
    team_login.scp_send_file(website_distribution, remote_fname)
    
    #checking that the file is there
    short_file_name = os.path.split(website_distribution)[1] 
    remote_fname = "/home/%s/%s" % (team_login.config.username, short_file_name)
    team_login.ssh_send_command("ls " + remote_fname )
    
    print("unzip web app")
    out = team_login.ssh_send_command("unzip " + remote_fname )
    print ("\t%s"% out)
    
    print("running deploy script '%s' remotely" % deploy_script_fname)
    out = team_login.ssh_send_command("bash " + deploy_script_fname  )
    print ("\t%s"% out)
    print('setup complete')
    print("%s\n"%(team_login.user_ssh_command()))
    print("http://%s"% team_login.config.hostname)
    
    # sudo apache2ctl restart
