from __future__ import print_function


def get_vpc_router_script(OPENVPN_SERVER_IP, OPENVPN_CLIENT_IP, machine_ip, ros_master_ip):
    
    return """#!/bin/bash
# Exit on error
set -ex
exec >/home/ubuntu/launch_stdout_stderr.log 2>&1


# Add OSRF repositories
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -

# ROS setup
sh -c 'echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list'
wget http://packages.ros.org/ros.key -O - | sudo apt-key add -

# Multiverse is needed to install some pandora server related packages
cat << DELIM_APT >> /etc/apt/sources.list
# Enable multiverse for pandora
deb http://archive.ubuntu.com/ubuntu precise multiverse
deb-src http://archive.ubuntu.com/ubuntu precise multiverse
deb http://archive.ubuntu.com/ubuntu precise-updates multiverse
deb-src http://archive.ubuntu.com/ubuntu precise-updates multiverse
DELIM_APT

apt-get update

apt-get install -y ntp
apt-get install -y openvpn

cat <<DELIM > /etc/openvpn/openvpn.conf
dev tun
ifconfig """ + OPENVPN_SERVER_IP + " " + OPENVPN_CLIENT_IP + """
secret static.key
DELIM
openvpn --genkey --secret /etc/openvpn/static.key
service openvpn restart
chmod 644 /etc/openvpn/static.key
sysctl -w net.ipv4.ip_forward=1
iptables -A FORWARD -i tun0 -o eth0 -j ACCEPT
iptables -A FORWARD -o tun0 -i eth0 -j ACCEPT

# That could be removed if ros-comm becomes a dependency of cloudsim-client-tools
sudo apt-get install -y ros-fuerte-ros-comm

# roscore is in simulator's machine
cat <<DELIM >> /etc/environment
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311
export ROS_IP=""" + machine_ip + """
source /opt/ros/fuerte/setup.sh
DELIM

apt-get install -y cloudsim-client-tools

# Create upstart vrc_sniffer job
cat <<DELIM > /etc/init/vrc_sniffer.conf
# /etc/init/vrc_sniffer.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_sniffer.py -t 11.8.0.2 -l vrc_current_outbound_latency > /var/log/vrc_sniffer.log 2>&1

respawn
DELIM

# Create upstart vrc_controller job
cat <<DELIM > /etc/init/vrc_controller.conf
# /etc/init/vrc_controller.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -s 0.5 -v -d eth0 > /var/log/vrc_controller.log 2>&1

respawn
DELIM

# Create upstart vrc_bandwidth job
cat <<DELIM > /etc/init/vrc_bandwidth.conf
# /etc/init/vrc_bandwidth.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero<caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_wrapper.sh vrc_bandwidth.py -d /tmp > /var/log/vrc_bandwidth.log 2>&1

respawn
DELIM

# start vrc_sniffer and vrc_controllers
start vrc_sniffer
start vrc_controller
start vrc_bandwidth

mkdir /home/ubuntu/cloudsim
mkdir /home/ubuntu/cloudsim/setup
touch /home/ubuntu/cloudsim/setup/done
chown -R ubuntu:ubuntu /home/ubuntu/cloudsim


# Install pandora dependencies
apt-get install -y snmp snmpd libtime-format-perl libxml-simple-perl libdbi-perl libnetaddr-ip-perl libhtml-parser-perl nmap traceroute libio-socket-inet6-perl libhtml-tree-perl libsnmp-perl snmp-mibs-downloader libio-socket-multicast-perl libsnmp-perl libjson-perl xprobe  libdbd-mysql-perl libxml-twig-perl

sudo debconf-set-selections <<< 'mysql-server-5.5 mysql-server/root_password password pass'
sudo debconf-set-selections <<< 'mysql-server-5.5 mysql-server/root_password_again password pass'
sudo apt-get -y install mysql-server

# Install pandora console (needed for server)
apt-get install php5 php5-curl mysql-client php5-snmp php5-gd php5-mysql php-db php5-xmlrpc php-gettext php5 curl graphviz dbconfig-common php5-ldap apache2

wget 'http://downloads.sourceforge.net/project/pandora/Pandora%20FMS%204.0.3/Debian_Ubuntu%20%28DEB%29/pandorafms.console_4.0.3-130118.deb?r=http%3A%2F%2Fwww.google.com%2Furl%3Fq%3Dhttp%253A%252F%252Fsourceforge.net%252Fprojects%252Fpandora%252Ffiles%252FPandora%252520FMS%2525204.0.3%252FDebian_Ubuntu%252520%252528DEB%252529%252Fpandorafms.console_4.0.3-130118.deb%252Fdownload%26sa%3DD%26sntz%3D1%26usg%3DAFQjCNH_XgMlgnQgJalqcGfLarJZO47pXQ&ts=1364237927&use_mirror=freefr' -O /tmp/pandora_console.deb

dpkg -i /tmp/pandora_console.deb

export MYSQL_PASS="pass"
mysql -u root -p${MYSQL_PASS} <<< "CREATE DATABASE pandora;"
mysql -u root -p${MYSQL_PASS} -Dpandora < /var/www/pandora_console/pandoradb.sql
mysql -u root -p${MYSQL_PASS} -Dpandora < /var/www/pandora_console/pandoradb_data.sql

cat << DELIM_PANDORA > /var/www/pandora_console/include/config.php
<?php
\$config["dbtype"] = "mysql";        
\$config["dbname"] = "pandora";               // MySQL DataBase name
\$config["dbuser"] = "root";                  // DB User
\$config["dbpass"] = "${MYSQL_PASS}";         // DB Password
\$config["dbhost"] = "localhost";              // DB Host
\$config["homedir"] = "/var/www/pandora_console"; // Config homedir
\$config["homeurl"] = "/pandora_console"; // Base URL
?>

error_reporting(E_ALL);

$ownDir = dirname(__FILE__) . '/';
include ($ownDir . "config_process.php");
DELIM_PANDORA

rm /var/www/pandora_console/install.php

# Install pandora server 
wget 'http://downloads.sourceforge.net/project/pandora/Tools%20and%20dependencies%20%28All%20versions%29/DEB%20Debian%2C%20Ubuntu/wmi-client_0112-1_amd64.deb?r=http%3A%2F%2Fsourceforge.net%2Fprojects%2Fpandora%2Ffiles%2FTools%2520and%2520dependencies%2520%2528All%2520versions%2529%2FDEB%2520Debian%252C%2520Ubuntu%2F&ts=1363026186' -O /tmp/wmi-client_0112-1.deb
wget 'http://downloads.sourceforge.net/project/pandora/Pandora%20FMS%204.0.3/Debian_Ubuntu%20%28DEB%29/pandorafms.server_4.0.3-130118.deb?r=http%3A%2F%2Fwww.google.com%2Furl%3Fq%3Dhttp%253A%252F%252Fsourceforge.net%252Fprojects%252Fpandora%252Ffiles%252FPandora%252520FMS%2525204.0.3%252FDebian_Ubuntu%252520%252528DEB%252529%252Fpandorafms.server_4.0.3-130118.deb%252Fdownload%26sa%3DD%26sntz%3D1%26usg%3DAFQjCNEQI2WsLiDqi0cWs7Z3JYttkuwZHA&ts=1363025800&use_mirror=heanet' -O /tmp/pandora_server_4.0.3.deb

dpkg -i /tmp/wmi-client_0112-1.deb
dpkg -i /tmp/pandora_server_4.0.3.deb

sed -i -e 's:servername.*:servername router-server:' /etc/pandora/pandora_server.conf
sed -i -e 's:dbpass.*:dbpass pass:' /etc/pandora/pandora_server.conf
sed -i -e 's:dbuser.*:dbuser root:' /etc/pandora/pandora_server.conf
/etc/init.d/pandora_server start

# Install pandora agent
wget 'http://downloads.sourceforge.net/project/pandora/Pandora%20FMS%204.0.3/Debian_Ubuntu%20%28DEB%29/pandorafms.agent_unix_4.0.3-130118.deb?r=http%3A%2F%2Fwww.google.com%2Furl%3Fq%3Dhttp%253A%252F%252Fsourceforge.net%252Fprojects%252Fpandora%252Ffiles%252FPandora%252520FMS%2525204.0.3%252FDebian_Ubuntu%252520%252528DEB%252529%252Fpandorafms.agent_unix_4.0.3-130118.deb%252Fdownload%26sa%3DD%26sntz%3D1%26usg%3DAFQjCNGiocSiDqQuZ8vPfT7prYp3JdO04w&ts=1363971857&use_mirror=ignum' -O /tmp/pandora_agent.deb

dpkg -i /tmp/pandora_agent.deb
/etc/init.d/pandora_agent start

"""

"""
Create a service that persist out routing rules accross reboots
"""
def get_vpc_open_vpn(OPENVPN_CLIENT_IP, TS_IP):
    
    s  = """

cat <<DELIM > /etc/init.d/vpcroute
#! /bin/sh

case "\$1" in
  start|"")
        route add """ + OPENVPN_CLIENT_IP+""" gw """ + TS_IP+"""
    ;;
  stop)
        route del """ + OPENVPN_CLIENT_IP+""" gw """ + TS_IP+"""
    ;;
  *)
    echo "Usage: vpcroute start|stop" >&2
    exit 3
    ;;
esac

:
DELIM

chmod +x  /etc/init.d/vpcroute 
ln -s /etc/init.d/vpcroute /etc/rc2.d/S99vpcroute

# invoke it now to add route to the router
/etc/init.d/vpcroute start

""" 
    return s 

def get_open_vpn_single(client_ip,
                        server_ip):
    
    s = """
    
cat <<DELIM >  /home/ubuntu/openvpn.config  
dev tun
ifconfig """ + server_ip + " " + client_ip + """
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
    

def get_cloudsim_startup_script():
    s = """#!/bin/bash
# Exit on error
set -ex
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
chown -R ubuntu:ubuntu /home/ubuntu/

apt-get update

echo "Installing packages" >> /home/ubuntu/setup.log

apt-get install -y unzip zip
echo "unzip installed" >> /home/ubuntu/setup.log

# install mercurial and fetch latest version of the Team Login website
apt-get install -y mercurial
echo "mercurial installed" >> /home/ubuntu/setup.log

#apt-get install -y cloud-utils
#echo "cloud-utils installed" >> /home/ubuntu/setup.log

apt-get install -y ntp
echo "ntp installed" >> /home/ubuntu/setup.log

apt-get install -y apache2
echo "apache2 installed" >> /home/ubuntu/setup.log

# apt-get install -y libapache2-mod-python
# echo "apache2 with mod-python installed" >> /home/ubuntu/setup.log

apt-get install -y redis-server python-pip
pip install redis
echo "redis installed" >> /home/ubuntu/setup.log

sudo pip install --upgrade boto
echo "boto installed" >> /home/ubuntu/setup.log


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
 
touch /home/ubuntu/cloudsim/setup/done
echo "STARTUP COMPLETE" >> /home/ubuntu/setup.log
"""

    return s
    

def get_drc_startup_script(open_vpn_script, machine_ip, drc_package_name, ros_master_ip="10.0.0.51"):
    
    s = """#!/bin/bash
# Exit on error
set -ex
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

echo \`date\` "\$1 \$2 \$3" >> /home/ubuntu/cloudsim/start_sim.log

. /usr/share/drcsim/setup.sh 
export ROS_IP=""" + machine_ip +""" 
export GAZEBO_IP=""" + machine_ip +"""
export DISPLAY=:0 
roslaunch \$1 \$2 \$3 gzname:=gzserver  &

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/stop_sim.bash

killall -INT roslaunch

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/ros.bash

# To connect via ROS:

# ROS's setup.sh will overwrite ROS_PACKAGE_PATH, so we'll first save the existing path
oldrpp=$ROS_PACKAGE_PATH

. /usr/share/drcsim/setup.sh
eval export ROS_PACKAGE_PATH=\$oldrpp:\\$ROS_PACKAGE_PATH
export ROS_IP=""" + machine_ip +"""
export ROS_MASTER_URI=http://""" + ros_master_ip + """:11311 

export GAZEBO_IP=""" + machine_ip +"""
export GAZEBO_MASTER_URI=http://""" + ros_master_ip + """:11345

DELIM

cat <<DELIM > /home/ubuntu/cloudsim/ping_gl.bash

DISPLAY=localhost:0 timeout 10 glxinfo

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
    
#
# The BusID is given by lspci (but lspci gives it in hex, and BusID needs dec)
# This value is required for Tesla cards
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

echo "install """ + drc_package_name+ """ ">> /home/ubuntu/setup.log
apt-get install -y """ + drc_package_name+ """

echo "Updating bashrc file">> /home/ubuntu/setup.log

cat <<DELIM >> /home/ubuntu/.bashrc
# CloudSim
. /usr/share/drcsim/setup.sh
export DISPLAY=:0 
export ROS_IP="""    + machine_ip + """
export GAZEBO_IP=""" + machine_ip + """

DELIM

echo "install cloudsim-client-tools" >> /home/ubuntu/setup.log
apt-get install -y cloudsim-client-tools

# Create upstart vrc_sniffer job
cat <<DELIM > /etc/init/vrc_sniffer.conf
# /etc/init/vrc_sniffer.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_sniffer.py -t 11.8.0.2 -l vrc_current_outbound_latency > /var/log/vrc_sniffer.log 2>&1

respawn
DELIM

# Create upstart vrc_controller job
cat <<DELIM > /etc/init/vrc_controller.conf
# /etc/init/vrc_controller.conf

description "OSRF cloud simulation platform"
author  "Carlos Aguero <caguero@osrfoundation.org>"

start on runlevel [234]
stop on runlevel [0156]

exec vrc_controller.py -f 0.25 -cl vrc_current_outbound_latency -v -d eth0 > /var/log/vrc_controller.log 2>&1

respawn
DELIM

# start vrc_sniffer and vrc_controllers
start vrc_sniffer
start vrc_controller

rm `which vrc_bandwidth.py`

# Install pandora agent
wget 'http://downloads.sourceforge.net/project/pandora/Pandora%20FMS%204.0.3/Debian_Ubuntu%20%28DEB%29/pandorafms.agent_unix_4.0.3-130118.deb?r=http%3A%2F%2Fwww.google.com%2Furl%3Fq%3Dhttp%253A%252F%252Fsourceforge.net%252Fprojects%252Fpandora%252Ffiles%252FPandora%252520FMS%2525204.0.3%252FDebian_Ubuntu%252520%252528DEB%252529%252Fpandorafms.agent_unix_4.0.3-130118.deb%252Fdownload%26sa%3DD%26sntz%3D1%26usg%3DAFQjCNGiocSiDqQuZ8vPfT7prYp3JdO04w&ts=1363971857&use_mirror=ignum' -O /tmp/pandora_agent.deb

dpkg -i /tmp/pandora_agent.deb
sed -i -e 's:server_ip.*:server_ip 10.0.0.50:' /etc/pandora/pandora_agent.conf
/etc/init.d/pandora_agent start

touch /home/ubuntu/cloudsim/setup/done

"""
    return s

def create_vpn_connect_file(openvpn_client_ip):
    return """#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ $UID != 0 ]; then
  echo "You're not root.  Run this script under sudo."
  exit 1
fi

echo "Killing other openvpn connections..."
killall openvpn || true
openvpn --config  $DIR/openvpn.config >/dev/null 2>&1 &

echo "VPN ready.  To kill it:"
echo "    sudo killall openvpn"
"""

def create_vpc_vpn_connect_file(openvpn_client_ip):
    return """#!/bin/bash
set -e
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

if [ $UID != 0 ]; then
  echo "You're not root.  Run this script under sudo."
  exit 1
fi

echo "Killing other openvpn connections..."
killall openvpn || true
openvpn --config  $DIR/openvpn.config >/dev/null 2>&1 &

# Wait for tun0 to come up, then add a static route to the 10.0.0.0/24 network, which is the VPC on the other side
# of the router.
while ! ifconfig tun0 || test -z "`ifconfig tun0 | grep 'inet addr'`" 2>/dev/null; do
  echo "Waiting for tun0 to come up..."
  sleep 1
done

echo "Adding route to 10.0.0.0/24 network"
route add -net 10.0.0.0 netmask 255.255.255.0 gw """ + openvpn_client_ip + """

echo "VPN ready.  To kill it:"
echo "    sudo killall openvpn"
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

def create_ros_connect_file(machine_ip, master_ip ):
    
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
export ROS_IP=""" + machine_ip + """
export ROS_MASTER_URI=http://""" + master_ip + """:11311 

export GAZEBO_IP=""" + machine_ip + """
export GAZEBO_MASTER_URI=http://""" + master_ip + """:11345
                
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


if __name__ == "__main__":
    
    print("MAIN")
    
    OPENVPN_SERVER_IP='11.8.0.1'
    OPENVPN_CLIENT_IP='11.8.0.2'
    drc_package_name = 'drcsim'
    open_vpn_script = get_open_vpn_single(OPENVPN_CLIENT_IP, OPENVPN_SERVER_IP)
    SIM_SCRIPT = get_drc_startup_script(open_vpn_script, OPENVPN_SERVER_IP, drc_package_name)

    print(SIM_SCRIPT)
    
    
    
