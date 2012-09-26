from __future__ import print_function
import uuid
import os
import time
import subprocess

import common

#IMAGE_ID = 'ami-4438b474' # Vanilla 64-bit Ubuntu 12.04
IMAGE_ID = 'ami-82fa58eb' # Vanilla 64-bit Ubuntu 12.04 for us-east
#IMAGE_ID = 'ami-44028d74' # a custom AMI used in testing
#IMAGE_ID = 'ami-98fa58f1' # Ubuntu Server 12.04 LTS for Cluster Instances
INSTANCE_TYPE = 't1.micro' # freebie
#INSTANCE_TYPE = 'm1.small' # $0.08/hour
#INSTANCE_TYPE = 'cg1.4xlarge' # $2.10/hour; only available in us-east
# Security groups.  'openvpn' is configured to allow ssh and openvpn
SECURITY_GROUPS = ['openvpn']
# User name.  Default is 'ubuntu'
USERNAME = 'ubuntu'
# Ubuntu distro name
DISTRO = 'precise'
# Source list
SOURCES_LIST = 'data/sources.list'
# Startup script
STARTUP_SCRIPT = """#!/bin/bash
# Exit on error
set -e

# Overwrite the sources.list file with different content
cat <<DELIM > /etc/apt/sources.list
%s
DELIM

apt-get update

# install X, with nvidia drivers
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` nvidia-current nvidia-current-dev gnome-session-fallback

# configure X
cat <<DELIM > /etc/X11/xorg.conf
Section "ServerLayout"
    Identifier     "Layout0"
    Screen      0  "Screen0"
EndSection
Section "Monitor"
    Identifier     "Monitor0"
    VendorName     "Unknown"
    ModelName      "Unknown"
    HorizSync       28.0 - 33.0
    VertRefresh     43.0 - 72.0
    Option         "DPMS"
EndSection
Section "Device"
    Identifier     "Device0"
    Driver         "nvidia"
    BusID          "PCI:0:3:0"
    VendorName     "NVIDIA Corporation"
EndSection
Section "Screen"
    Identifier     "Screen0"
    Device         "Device0"
    Monitor        "Monitor0"
    DefaultDepth    24
    SubSection     "Display"
        Depth       24
    EndSubSection
EndSection
DELIM

# setup auto xsession login
echo "
[SeatDefaults]
greeter-session=unity-greeter
autologin-user=%s
autologin-user-timeout=0
user-session=gnome-fallback
" > /etc/lightdm/lightdm.conf
initctl stop lightdm || true
initctl start lightdm 

# Install ROS.
# For now, just pull Gazebo from Fuerte.  In the future, give 
# options here.
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
wget http://packages.ros.org/ros.key -O - | apt-key add -
apt-get update
apt-get -y install ros-fuerte-pr2-simulator ros-fuerte-arm-navigation ros-fuerte-pr2-teleop-app ros-fuerte-pr2-object-manipulation ros-fuerte-pr2-navigation

# Install and start openvpn.  Do this last, because we're going to 
# infer that the machine is ready from the presence of the 
# openvpn static key file.
apt-get install -y openvpn
openvpn --genkey --secret %s
cat <<DELIM > openvpn.config
dev tun
ifconfig %s %s
secret %s
DELIM
chmod 644 %s
# Set up for autostart by dropping this stuff in /etc/openvpn
cp openvpn.config /etc/openvpn/openvpn.conf
cp %s /etc/openvpn/%s
service openvpn start
"""

TEAM_LOGIN_STARTUP_SCRIPT = """#!/bin/bash

echo "In the beginning was the Computer" > /home/ubuntu/STARTUP_SCRIPT_LOG

# Exit on error
set -e
echo "config: exit on error" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# Overwrite the sources.list file with different content
cat <<DELIM > /etc/apt/sources.list
%s
DELIM
echo "sources.list overriden" >> /home/ubuntu/STARTUP_SCRIPT_LOG


apt-get update
echo "SYSTEM UPDATED" >> /home/ubuntu/STARTUP_SCRIPT_LOG

echo "Installing packages" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# install mercurial and fetch latest version of the Team Login website
apt-get install -y mercurial
echo "mercurial installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG


# apt-get install -y git
# git clone git://github.com/bmuller/mod_auth_openid.git
# apt-get install -y build-essential
# libtool
# automake


apt-get install -y apache2
echo "apache2 installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

# apt-get install -y libapache2-mod-python
echo "apache2-mod-python installed" >> /home/ubuntu/STARTUP_SCRIPT_LOG

 
apt-add-repository -y ppa:rye/ppa
apt-get update
apt-get install -y libapache2-mod-auth-openid
echo "libapache2-mod-auth-openid 0.6 installed from ppa:rye/ppa" >> /home/ubuntu/STARTUP_SCRIPT_LOG



# restart apache2 
# /etc/init.d/apache2 restart

# to list installed modules  
# apachectl -t -D DUMP_MODULES


echo "STARTUP COMPLETE" >> /home/ubuntu/STARTUP_SCRIPT_LOG

"""

def load_startup_script(distro, username, machine_id, server_ip, client_ip):
    # TODO: Make this less fragile with a proper templating language (e.g, empy)
    sources_list = open('data/sources.list-%s'%(distro)).read()
    key = common.OPENVPN_STATIC_KEY_FNAME
    startup_script = STARTUP_SCRIPT%(sources_list, username, key, server_ip, client_ip, key, key, key, key)
    return startup_script


def create_machine_instance(credentials_ec2, 
                            pem_key_directory, 
                            image_id, instance_type, 
                            username, 
                            distro):
    
    
    ec2 = common.create_ec2_proxy(credentials_ec2)

    # Create key pair to use for SSH access.  Note that 
    # create_key_pair() registers the named key with AWS.
    uid = str(uuid.uuid1())
    cfg_dir=os.path.join(pem_key_directory, uid)
    if os.path.exists(cfg_dir):
        print('Directory/file %s already exists; bailing'%(cfg_dir))
        raise Exception('UUID creation did not meet expectations')
    os.makedirs(cfg_dir)
    kp_name = 'key-%s'%(uid)
    kp = ec2.create_key_pair(kp_name)
    kp_fname = os.path.join(cfg_dir, kp_name + '.pem')
    # save the ssh key
    kp.save(cfg_dir)
    return (uid, kp_name, kp_fname)
        


def create_team_login_instance():

    credentials_ec2 = "boto_cfg.ini"
    pem_key_directory = "team_login_pem" 
    image_id = "ami-137bcf7a"
    instance_type="t1.micro"
    security_group = "TeamLogin"
    username = "ubuntu" 
    distro = "precise"
    

    print("create_team_login_instance")
    print("    BOTO file: %s" % credentials_ec2)
    print("    pem_key_directory: %s" % pem_key_directory)
    print("    image_id: %s" % image_id)
    print("    instance_type: %s" % instance_type)
    print("    security_group: %s" % security_group)
    print("    username: %s" % username)
    print("    distro: %s" % distro)
#    print("startup_script",startup_script)

    sources_list = open('data/sources.list-%s'%(distro)).read()
    startup_script = TEAM_LOGIN_STARTUP_SCRIPT % (sources_list)
    
#    if len(startup_script) > 0 :
#        print(startup_script)
#        return
    
    uid, kp_name, kp_fname = create_machine_instance(credentials_ec2, pem_key_directory, image_id, instance_type, username, distro)
    try:
        # Start it up
        #print("Load startup script: image_id %s, security_group %s" % (image_id, security_group ) )
        ec2 = common.create_ec2_proxy(credentials_ec2)
        res = ec2.run_instances(    image_id=image_id, 
                                    key_name=kp_name, 
                                    instance_type=instance_type, 
                                    security_groups=[security_group], user_data=startup_script)
        
        print('Creating instance "%s\nkey file %s"'%(res.id, kp_fname))
        
        # Wait for it to boot to get an IP address
        while True:
            done = False
            for r in ec2.get_all_instances():
                if r.id == res.id and r.instances[0].public_dns_name:
                    done = True
                    break
            if done:
                break
            else:
                time.sleep(0.1)

        inst = r.instances[0]
        hostname = inst.public_dns_name
        aws_id = inst.id

        print("Associating the instance with an Elastic IP:")
        address = ec2.allocate_address()
        print("\t%s" % address.public_ip)
        res = ec2.associate_address(inst.id, address.public_ip)
        if not res:
            raise "Elastic IP failure"
        
        print ("ssh -i %s ubuntu@%s" % ( kp_fname, address.public_ip) )
        

        

    except Exception as e:
        # Clean up
        
        if os.path.exists(kp_fname):
            os.unlink(kp_fname)
            
        cfg_dir=os.path.join(pem_key_directory, uid)
        os.rmdir(cfg_dir)
        # re-raise
        raise
    

def create_ec2_instance(boto_config_file,
                        output_config_dir,
                        image_id=IMAGE_ID, 
                        instance_type=INSTANCE_TYPE,
                        security_groups=SECURITY_GROUPS,
                        username=USERNAME,
                        distro=DISTRO):

    ec2 = common.create_ec2_proxy(boto_config_file)

    # Create key pair to use for SSH access.  Note that 
    # create_key_pair() registers the named key with AWS.
    uid = str(uuid.uuid1())
    cfg_dir=os.path.join(output_config_dir, uid)
    if os.path.exists(cfg_dir):
        print('Directory/file %s already exists; bailing'%(cfg_dir))
        raise Exception('UUID creation did not meet expectations')
    os.makedirs(cfg_dir)
    kp_name = 'key-%s'%(uid)
    kp = ec2.create_key_pair(kp_name)
    kp_fname = os.path.join(cfg_dir, kp_name + '.pem')

    try:
        # Start it up
        print("Load startup script: image_id %s, security_groups %s" % (image_id, security_groups ) )
        startup_script = load_startup_script(distro, username, uid, common.OV_SERVER_IP, common.OV_CLIENT_IP)
        res = ec2.run_instances(image_id=image_id, key_name=kp_name, instance_type=instance_type, security_groups=security_groups, user_data=startup_script)
        print('Creating instance %s...'%(res.id))

        # Wait for it to boot to get an IP address
        while True:
            done = False
            for r in ec2.get_all_instances():
                if r.id == res.id and r.instances[0].public_dns_name:
                    done = True
                    break
            if done:
                break
            else:
                time.sleep(0.1)

        inst = r.instances[0]
        hostname = inst.public_dns_name
        aws_id = inst.id

        # save the ssh key
        kp.save(cfg_dir)

        print('Waiting for sshd to respond...')
        # Wait for sshd to respond.  We check for readability of the static
        # key file because that's what we're going to scp next.
        #TODO: put a timeout in this loop
        #TODO: use Machine.test_ssh() instead of calling ssh directly
        
        cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', kp_fname, '%s@%s'%(USERNAME, hostname), 'ls', '/%s'%(common.OPENVPN_STATIC_KEY_FNAME)]
        print(cmd)
        while True:
            #cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', kp_fname, '%s@%s'%(USERNAME, hostname), 'ls', '/%s'%(common.OPENVPN_STATIC_KEY_FNAME)]
            po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = po.communicate()
            if po.returncode == 0:
                break
            else:
                time.sleep(0.1)
                
        print ("retrieve the openvpn key")
        # retrieve the openvpn key
        ov_key_fname = 'openvpn-%s.key'%(uid)
        cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-i', kp_fname, str('%s@%s:/%s'%(USERNAME, hostname, common.OPENVPN_STATIC_KEY_FNAME)), os.path.join(cfg_dir, ov_key_fname)]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode != 0:
            raise Exception('scp failed: %s'%(err))
        # write hostname to file
        hostname_fname = os.path.join(cfg_dir, common.HOSTNAME_FNAME)
        with open(hostname_fname, 'w') as hostname_file:
            hostname_file.write(hostname) 
        # write AWS ID to file
        aws_id_fname = os.path.join(cfg_dir, common.AWS_ID_FNAME)
        with open(aws_id_fname, 'w') as aws_id_file:
            aws_id_file.write(aws_id) 
        # write username to file
        username_fname = os.path.join(cfg_dir, common.USERNAME_FNAME)
        with open(username_fname, 'w') as username_file:
            username_file.write(username) 
        # write botofile to file
        botofile_fname = os.path.join(cfg_dir, common.BOTOFILE_FNAME)
        with open(botofile_fname, 'w') as botofile_file:
            botofile_file.write(boto_config_file) 
        # create openvpn config file
        ov_cfgfile_base = common.OPENVPN_CONFIG_FNAME
        ov_cfgfile = os.path.join(cfg_dir, ov_cfgfile_base)
        with open(ov_cfgfile, 'w') as ovcfg:
            ovcfg.write('remote %s\n'%(hostname))
            ovcfg.write('dev tun\n')
            ovcfg.write('ifconfig %s %s\n'%(common.OV_CLIENT_IP, common.OV_SERVER_IP))
            ovcfg.write('secret %s\n'%(ov_key_fname))
    except Exception as e:
        # Clean up
        kp.delete()
        if os.path.exists(kp_fname):
            os.unlink(kp_fname)
        os.rmdir(cfg_dir)
        # re-raise
        raise

if __name__ == '__main__':
    print ("create_ec2_instance::__main__\n\n")
    create_team_login_instance()
    
