from create_ec2_instance import Machine2

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
#apt-get install -y mercurial
#echo "mercurial installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG


apt-get install -y apache2
echo "apache2 installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# apt-get install -y libapache2-mod-python
# echo "apache2 with mod-python installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

 
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

mv /home/ubuntu/STARTUP_SCRIPT_LOG /home/ubuntu/STARTUP_SCRIPT_LOG_DONE
echo "STARTUP COMPLETE" >> /home/ubuntu/STARTUP_SCRIPT_LOG



"""

def generate_setup_script(distro):
    sources_list = open('data/sources.list-%s'%(distro)).read()
    startup_script = TEAM_LOGIN_STARTUP_SCRIPT_TEMPLATE % (sources_list)
    return startup_script

if __name__ == '__main__':
    print ("create_team_login_instance::__main__\n\n")
   #  create_team_login_instance()

    
    team_login =  Machine2(credentials_ec2 = "boto_cfg.ini",
            pem_key_directory = "team_login_pem", 
            image_id = "ami-137bcf7a",
            instance_type= "m1.small", # "t1.micro"
            security_groups = ["TeamLogin"],
            username = "ubuntu", 
            distro = "precise")
    
    website_distribution = "cloudsim.zip"
    deploy_script_fname = "/home/%s/cloudsim/deploy.sh" % team_login.username 
    local_fname = "../../../%s" % website_distribution
    remote_fname = '/home/%s' % (team_login.username)
    
    startup_script = generate_setup_script(team_login.distro, )
    team_login.launch(startup_script)
    print("Machine launched at: %s"%(team_login.hostname))
    print("\nIn case of emergency:\n\n%s\n\n"%(team_login.user_ssh_command()))
    print("Waiting for ssh")
    team_login.ssh_wait_for_ready()
    print("Good to go.")
    
    print("uploading '%s' to the server to '%s'" % (local_fname, remote_fname) )
    team_login.scp_send_file(local_fname, remote_fname)
    
    #checking that the file is there
    remote_fname = "/home/%s/%s" % (team_login.username, website_distribution)
    team_login.ssh_send_command(["ls", remote_fname ] )
    
    print("unzip web app")
    out = team_login.ssh_send_command(["unzip" , remote_fname] )
    print ("\t%s"% out)
    
    print("run deploy script '%s" % deploy_script_fname)
    out = team_login.ssh_send_command(["bash", deploy_script_fname ] )
    print ("\t%s"% out)

    # sudo apache2ctl restart
