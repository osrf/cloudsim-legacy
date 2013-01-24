from __future__ import print_function



def get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP):    
    return """#!/bin/bash
# Exit on error
set -e
exec >/home/ubuntu/launch_stdout_stderr.log 2>&1

apt-get install -y openvpn
cat <<DELIM > /etc/openvpn/openvpn.conf
dev tun
ifconfig """ + OPENVPN_SERVER_IP+ " " + OPENVPN_CLIENT_IP + """
secret static.key
DELIM
openvpn --genkey --secret /etc/openvpn/static.key
service openvpn restart
chmod 644 /etc/openvpn/static.key
sysctl -w net.ipv4.ip_forward=1
iptables -A FORWARD -i tun0 -o eth0 -j ACCEPT
iptables -A FORWARD -o tun0 -i eth0 -j ACCEPT

mkdir /home/ubuntu/cloudsim
mkdir /home/ubuntu/cloudsim/setup
touch /home/ubuntu/cloudsim/setup/done
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim

"""

def get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP):
    
    s  = """
# Add route 
route add """ + OPENVPN_CLIENT_IP + "  gw " + TS_IP  + """

""" 
    return s 

def get_open_vpn_single(client_ip,
                        server_ip):
    
    s = """
    
cat <<DELIM >  /home/ubuntu/openvpn.config  
dev tun
ifconfig """ + client_ip + " " + server_ip + """
secret static.key  

DELIM

echo "Installing openvpn" >> /home/ubuntu/setup.log
apt-get install -y openvpn

echo "Generating openvpn key" >> /home/ubuntu/setup.log
openvpn --genkey --secret static.key

echo "Setting key permissions" >> /home/ubuntu/setup.log
chmod 644 static.key

echo "Set up for autostart by copying conf to /etc/openvpn" >> /home/ubuntu/setup.log 
cp /home/ubuntu/openvpn.config /etc/openvpn/openvpn.conf
cp static.key /etc/openvpn/static.key    

echo "openvpn setup complete" >> /home/ubuntu/setup.log

"""
    return s
    

def get_drc_startup_script(open_vpn_script):
    
    s = """#!/bin/bash
# Exit on error
set -e
# Redirect everybody's output to a file
logfile=/home/ubuntu/launch_stdout_stderr.log
exec > $logfile 2>&1


cat <<DELIM > /etc/apt/sources.list

##
## cloudsim 
##
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

DELIM

mkdir /home/ubuntu/cloudsim
mkdir /home/ubuntu/cloudsim/setup

cat <<DELIM > /home/ubuntu/cloudsim/start_sim.bash

echo date "$1 $2 $3" >> /home/ubuntu/cloudsim/start_sim.log

. /usr/share/drcsim/setup.sh 
export ROS_IP= 10.0.0.51 
export GAZEBO_IP= 10.0.0.51 
export DISPLAY=:0 
roslaunch $1 $2 
gzname:=gzserver $3  &

DELIM

chown -R ubuntu:ubuntu /home/ubuntu/cloudsim  

# Add ROS and OSRF repositories
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

date >> /home/ubuntu/setup.log
echo 'setting up the ros and drc repos keys' >> /home/ubuntu/setup.log
wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -
    
echo "update packages" >> /home/ubuntu/setup.log
apt-get update

""" + open_vpn_script + """
    
echo "install X, with nvidia drivers" >> /home/ubuntu/setup.log
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` nvidia-current nvidia-current-dev gnome-session-fallback
    

cat <<DELIM > etc/X11/xorg.conf
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


echo "setup auto xsession login" >> /home/ubuntu/setup.log

echo "
[SeatDefaults]
greeter-session=unity-greeter
autologin-user=ubuntu
autologin-user-timeout=0
user-session=gnome-fallback
" > /etc/lightdm/lightdm.conf
initctl stop lightdm || true
initctl start lightdm 

apt-get install -y ntp 

echo "install drc" >> /home/ubuntu/setup.log
apt-get install -y drcsim
echo ". /usr/share/drcsim/setup.sh" >> /home/ubuntu/.bashrc

echo "install cloudsim-client-tools" >> /home/ubuntu/setup.log
apt-get install -y cloudsim-client-tools    
    

 
touch /home/ubuntu/cloudsim/setup/done

"""
    return s


def create_vpn_connect_file():
    return """#!bin/bash
sudo openvpn --config openvpn.config"

"""

def create_openvpn_client_cfg_file(hostname,
                            client_ip,
                            server_ip ):
    s = """
remote """ + hostname + """
dev tun
ifconfig """ + client_ip + " " + server_ip +  """
secret openvpn.key
    """ 
    return s

def create_ros_connect_file(openvpn_client_ip, openvpn_server_ip ):
    
    s = """
# To connect via ROS:
# 1. Connect via OpenVPN 
# 2. Download this file: [ros.sh] <- autogenerated with the right IP addresses
# 3. In a terminal, go to the directory containing that file.
# 4. Execute the following command:
#    . ros.bash
# 5. Now your environment is configured to connect to a ROS master running on this machine.

# ROS's setup.sh will overwrite ROS_PACKAGE_PATH, so we'll first save the existing path
oldrpp=$ROS_PACKAGE_PATH
. /opt/ros/fuerte/setup.sh
eval export ROS_PACKAGE_PATH=$oldrpp:\$ROS_PACKAGE_PATH
export ROS_IP=""" + openvpn_client_ip + """
export ROS_MASTER_URI=http://""" + openvpn_server_ip + """:11311 

#export GAZEBO_IP=""" + openvpn_client_ip + """
#export GAZEBO_MASTER_URI=http://""" + openvpn_server_ip + """:11345
                
    """  
    return s

def create_ssh_connect_file(key_file, ip):
    s = """#!/bin/bash

#
# This command connects you to the simulation
# It passes a keyfile to the ssh command and logs you in as the 
# default user on the cloud machine

# ssh -i """ + key_file + " ubuntu@" + ip + """
    
#
# This commands is similar, but it suppresses prompts and can be invoked 
# from any directory
#    
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/""" + key_file + " ubuntu@" + ip + """
    """ 
    return s