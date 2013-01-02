from __future__ import with_statement
from __future__ import print_function

import unittest
from  testing import get_test_runner

import commands
import constants


OPEN_VPN_KEY_FNAME = "openvpn.key"



SOURCES_LIST_PRECISE = """
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

"""


LAUNCH_SCRIPT_HEADER =  """#!/bin/bash
# Exit on error
set -e
# Redirect everybody's output to a file
logfile=/home/ubuntu/launch_stdout_stderr.log
exec > $logfile 2>&1

"""

def get_monitoring_tools_script(boundary_creds = None): 
    
    str =  """

echo "Installing network monitoring tools" >> /home/ubuntu/setup.log
date >> /home/ubuntu/setup.log

apt-get install -y ntp

"""
    if boundary_creds:
        str += """
curl -3 -s https://app.boundary.com/assets/downloads/setup_meter.sh > setup_meter.sh
chmod +x setup_meter.sh
./setup_meter.sh -d -i """ + boundary_creds 

    str += """
date >> /home/ubuntu/setup.log
echo "monitoring tools installed " >> /home/ubuntu/setup.log

""" 
    return str


INSTALL_VPN = """

echo "Installing openvpn" >> /home/ubuntu/setup.log
apt-get install -y openvpn

echo "Generating openvpn key" >> /home/ubuntu/setup.log
openvpn --genkey --secret static.key

echo "Setting key permissions" >> /home/ubuntu/setup.log
chmod 644 static.key

echo "Set up for autostart by copying conf to /etc/openvpn" >> /home/ubuntu/setup.log 
cp openvpn.config /etc/openvpn/openvpn.conf
cp static.key /etc/openvpn/static.key

echo "Start openvpn" >> /home/ubuntu/setup.log
service openvpn start

echo "vpn setup complete" >> /home/ubuntu/setup.log
"""


ROS_SETUP_STARTUP_SCRIPT = """

# Install ROS.
# For now, just pull Gazebo from Fuerte.  In the future, give 
# options here.
echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
wget http://packages.ros.org/ros.key -O - | apt-key add -
apt-get update
apt-get -y install ros-fuerte-pr2-simulator ros-fuerte-arm-navigation ros-fuerte-pr2-teleop-app ros-fuerte-pr2-object-manipulation ros-fuerte-pr2-navigation


"""

DRC_SIM_SETUP_STARTUP_SCRIPT = """

date >> /home/ubuntu/setup.log

echo "deb http://packages.ros.org/ros/ubuntu precise main" > /etc/apt/sources.list.d/ros-latest.list
echo "deb http://packages.osrfoundation.org/drc/ubuntu precise main" > /etc/apt/sources.list.d/drc-latest.list

date >> /home/ubuntu/setup.log
echo 'setting up the ros and drc repos keys' >> /home/ubuntu/setup.log
wget http://packages.ros.org/ros.key -O - | apt-key add -
wget http://packages.osrfoundation.org/drc.key -O - | apt-key add -

echo 'package update' >> /home/ubuntu/setup.log
apt-get update

echo 'installing the packages' >> /home/ubuntu/setup.log
date >> /home/ubuntu/setup.log
apt-get install -y drcsim
date >> /home/ubuntu/setup.log


"""

XGL_STARTUP_BEFORE = """

apt-get update

# install X, with nvidia drivers
apt-get install -y xserver-xorg xserver-xorg-core lightdm x11-xserver-utils mesa-utils pciutils lsof gnome-session nvidia-cg-toolkit linux-source linux-headers-`uname -r` nvidia-current nvidia-current-dev gnome-session-fallback

"""

XGL_STARTUP_AFTER = """

# setup auto xsession login
echo "
[SeatDefaults]
greeter-session=unity-greeter
autologin-user=ubuntu
autologin-user-timeout=0
user-session=gnome-fallback
" > /etc/lightdm/lightdm.conf
initctl stop lightdm || true
initctl start lightdm 


""" 


def create_openvpn_server_cfg_file(client_ip = constants.OV_CLIENT_IP,
                                   server_ip = constants.OV_SERVER_IP,
                                   key_file = constants.OPENVPN_STATIC_KEY_FNAME):

    s = """dev tun
ifconfig %s %s
secret %s"""  % (server_ip, client_ip, key_file)   
    return s
    

def create_openvpn_client_cfg_file(hostname,
                            client_ip = constants.OV_CLIENT_IP,
                            server_ip = constants.OV_SERVER_IP,
                            key_file =  OPEN_VPN_KEY_FNAME):
    s = """
remote %s
dev tun
ifconfig %s %s
secret %s
    """ % (hostname, client_ip, server_ip, key_file)
    return s

def create_ros_connect_file(openvpn_client_ip = constants.OV_CLIENT_IP, 
                    openvpn_server_ip = constants.OV_SERVER_IP):
    s = """
            
# To connect via ROS:
# 1. Connect via OpenVPN 
# 2. Download this file: [ros.sh] <- autogenerated with the right IP addresses
# 3. In a terminal, go to the directory containing that file.
# 4. Execute the following command:
#    . ros.sh
# 5. Now your environment is configured to connect to a ROS master running on this machine.
# 6. You may want to first [launch Gazebo|launch_page].

# ROS's setup.sh will overwrite ROS_PACKAGE_PATH, so we'll first save the existing path
oldrpp=$ROS_PACKAGE_PATH
. /opt/ros/fuerte/setup.sh
eval export ROS_PACKAGE_PATH=$oldrpp:\$ROS_PACKAGE_PATH
export ROS_IP=%s
export ROS_MASTER_URI=http://%s:11311 
                """  % (openvpn_client_ip, openvpn_server_ip)
    return s

def create_scp_download_file(key_file, ip, username = "ubuntu"):
    s = """#!/bin/bash

echo "Download remote file via scp"
echo "remote source " $1    
echo "local target " $2

# This commands suppresses prompts and can be invoked from any directory
  DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/%s %s@%s:$1 $2
    
    """ % (key_file, username, ip, key_file, username, ip)
    return s

def create_ssh_connect_file(key_file, ip, username = "ubuntu"):
    s = """#!/bin/bash

#
# This command connects you to the simulation
# It passes a keyfile to the ssh command and logs you in as the 
# default user on the cloud machine

# ssh -i %s %s@%s
    
#
# This commands is similar, but it suppresses prompts and can be invoked 
# from any directory
#    
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/%s %s@%s 
    """ % (key_file, username, ip, key_file, username, ip)
    return s

def create_vpn_static_key():
    status, output = commands.getstatusoutput("openvpn --genkey --secret /dev/stdout")
    if status:
        raise Exception("openvpn is not installed")
    return output 

    
def inject_file_into_script(file_path, file_content):
    
    script_lines = []
    script_lines.append("")
    script_lines.append("")
    script_lines.append("\ncat <<DELIM > %s" % file_path)
    script_lines.append(file_content)
    script_lines.append("DELIM")
    script_lines.append("")
    script_lines.append("")
    return "\n".join(script_lines)
    

def create_vpn_connect_file():
    return """#!bin/bash
sudo openvpn --config openvpn.config"

"""

def create_xorg_config_file():

    return """
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
"""
    
class ScriptTests(unittest.TestCase):

    def test_inject(self):
        
        machine_name = "gazebo_1234556"
        hostname = "toto.aws.com" 
        
        script = "#!/bin/bash\n\n"
        script += "mkdir %s\n" % machine_name
        # lines = output.split("\n")
        zip_dir_name = machine_name
        file_content = create_vpn_static_key()
        script += inject_file_into_script( "%s/static.key"% zip_dir_name, file_content )
        script += "chmod 644 %s/static.key\n" % machine_name

        file_content = create_openvpn_client_cfg_file(hostname)
        script += inject_file_into_script( "%s/%s" % (zip_dir_name, constants.OPENVPN_CONFIG_FNAME), file_content)
        
        file_content = create_ros_connect_file()
        script += inject_file_into_script("%s/ros.sh" % zip_dir_name, file_content )
        
        file_content = create_ssh_connect_file('key_file', 'ip', 'username')
        script += inject_file_into_script("%s/ssh.sh" % zip_dir_name, file_content )
        
        script += "zip -r %s.zip %s\n" %  (zip_dir_name, zip_dir_name)
        script += "rm -rf %s\n" %  (zip_dir_name)
        
        # print(script)
        with open("test.sh", 'w') as f:
            f.write(script)
        
        cmd = "bash test.sh"
        print('Executing: %s'% cmd)
        s,o = commands.getstatusoutput(cmd)
        print(s)
        print('done')
            
        

if __name__ == "__main__":
    print("STARTUP SCRIPT TESTS")
    unittest.main(testRunner = get_test_runner(), exit=False)          