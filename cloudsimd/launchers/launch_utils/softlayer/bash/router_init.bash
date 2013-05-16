#!/bin/bash

set -ex
exec > router_init.log 2>&1

DIR=$1 # /home/ubuntu/cloudsim


SIM_INITIAL_IP=$2
FC1_INITIAL_IP=$3
FC2_INITIAL_IP=$4

#
# The final addresses
#
# ROUTER_IP=10.0.0.50
SIM_IP=10.0.0.51
FC1_IP=10.0.0.52
FC2_IP=10.0.0.53

#
# We need this software to automate the addition of the ubuntu user
#
sudo apt-get install -y expect

# --------------------------------------------

cat <<DELIM > $DIR/change_ip.bash

#
# Assumes private IP starts with 10.41. rather than look for 
# $SIM_INITIAL_IP, $FC1_INITIAL_IP or $FC2_INITIAL_IP
#

#!/bin/bash
set -ex
exec > ./change_ip_to_\$1.log 2>&1

file=/etc/network/interfaces
new_ip=\$1

cp \$file \$file.bak
sed "s/^address 10.41.*/address \$new_ip/" \$file.bak > \$file

#
# Adjust the DNS to use Google instead of SoftLayer
#
echo "nameserver 8.8.8.8" > /etc/resolv.conf
echo "nameserver 8.8.4.4" >> /etc/resolv.conf

/etc/init.d/networking restart
echo done
DELIM

chmod +x $DIR/change_ip.bash

# change_ip.bash is easily run from the home directory on all machines
cp $DIR/change_ip.bash $DIR/..

 # --------------------------------------------

cat <<DELIM > $DIR/set_fc1_ip.bash
#!/bin/bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem $DIR/change_ip.bash ubuntu@$FC1_INITIAL_IP:change_ip.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_INITIAL_IP "nohup sudo ./change_ip.bash $FC1_IP > ssh_change_ip.out 2> ssh_change_ip.err < /dev/null &"

DELIM
chmod +x $DIR/set_fc1_ip.bash

# --------------------------------------------

cat <<DELIM > $DIR/set_fc2_ip.bash
#!/bin/bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem $DIR/change_ip.bash ubuntu@$FC2_INITIAL_IP:change_ip.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_INITIAL_IP "nohup sudo ./change_ip.bash $FC2_IP > ssh_change_ip.out 2> ssh_change_ip.err < /dev/null &"

DELIM
chmod +x $DIR/set_fc2_ip.bash

# --------------------------------------------

cat <<DELIM > $DIR/set_sim_ip.bash
#!/bin/bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem $DIR/change_ip.bash ubuntu@$SIM_INITIAL_IP:change_ip.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_INITIAL_IP "nohup sudo ./change_ip.bash $SIM_IP > ssh_change_ip.out 2> ssh_change_ip.err < /dev/null &"

DELIM
chmod +x $DIR/set_sim_ip.bash


# --------------------------------------------

cat <<DELIM > $DIR/dpkg_log_fc1.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP "tail -1 /var/log/dpkg.log"
DELIM
chmod +x $DIR/dpkg_log_fc1.bash


# --------------------------------------------


cat <<DELIM > $DIR/find_file_fc1.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP "ls \$1"
DELIM
chmod +x $DIR/find_file_fc1.bash

# --------------------------------------------


cat <<DELIM > $DIR/ssh_fc1.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP
DELIM
chmod +x $DIR/ssh_fc1.bash

# --------------------------------------------

cat <<DELIM > $DIR/fc1_init.bash
#!/bin/bash
set -ex
exec > $DIR/fc1_init.log 2>&1

chmod +x $DIR/fc1_startup_script.bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem $DIR/fc1_startup_script.bash ubuntu@$FC1_IP:fc1_startup_script.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP "nohup sudo ./fc1_startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &"

DELIM
chmod +x $DIR/fc1_init.bash


# --------------------------------------------

cat <<DELIM > $DIR/reboot_fc1.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP "sudo reboot"
DELIM
chmod +x $DIR/reboot_fc1.bash


# --------------------------------------------


cat <<DELIM > $DIR/dpkg_log_fc2.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP "tail -1 /var/log/dpkg.log"
DELIM
chmod +x $DIR/dpkg_log_fc2.bash


# --------------------------------------------


cat <<DELIM > $DIR/find_file_fc2.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP "ls \$1"
DELIM
chmod +x $DIR/find_file_fc2.bash

# --------------------------------------------


cat <<DELIM > $DIR/ssh_fc2.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP
DELIM
chmod +x $DIR/ssh_fc2.bash


# --------------------------------------------


cat <<DELIM > $DIR/reboot_fc2.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP "sudo reboot"
DELIM
chmod +x $DIR/reboot_fc2.bash


# --------------------------------------------


cat <<DELIM > $DIR/fc2_init.bash
#!/bin/bash
set -ex
exec > $DIR/fc2_init.log 2>&1

chmod +x $DIR/fc2_startup_script.bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem $DIR/fc2_startup_script.bash ubuntu@$FC2_IP:fc2_startup_script.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP "nohup sudo ./fc2_startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &"

DELIM
chmod +x $DIR/fc2_init.bash


# --------------------------------------------



cat <<DELIM > $DIR/dpkg_log_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "tail -1 /var/log/dpkg.log"
DELIM
chmod +x $DIR/dpkg_log_sim.bash


# --------------------------------------------


cat <<DELIM > $DIR/find_file_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "ls \$1"
DELIM
chmod +x $DIR/find_file_sim.bash

# --------------------------------------------


cat <<DELIM > $DIR/ssh_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP
DELIM
chmod +x $DIR/ssh_sim.bash

# --------------------------------------------


cat <<DELIM > $DIR/sim_init.bash
#!/bin/bash
set -ex
exec > $DIR/sim_init.log 2>&1

chmod +x $DIR/sim_startup_script.bash
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem $DIR/sim_startup_script.bash ubuntu@$SIM_IP:sim_startup_script.bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "nohup sudo ./sim_startup_script.bash > ssh_startup.out 2> ssh_startup.err < /dev/null &"

DELIM
chmod +x $DIR/sim_init.bash


# --------------------------------------------



cat <<DELIM > $DIR/reboot_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "sudo reboot"
DELIM
chmod +x $DIR/reboot_sim.bash


cat <<DELIM > $DIR/ping_gazebo.bash
#!/bin/bash
ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP ". /usr/share/drcsim/setup.sh; timeout 5 gztopic list"
DELIM
chmod +x $DIR/ping_gazebo.bash


cat <<DELIM > $DIR/ping_gl.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "DISPLAY=localhost:0 timeout 5 glxinfo"
DELIM
chmod +x $DIR/ping_gl.bash


cat <<DELIM > $DIR/stop_sim.bash
#!/bin/bash
sudo stop vrc_netwatcher
sudo stop vrc_bytecounter
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "bash cloudsim/stop_sim.bash"
sudo iptables -F FORWARD
DELIM
chmod +x $DIR/stop_sim.bash


cat <<DELIM > $DIR/start_sim.bash
#!/bin/bash
sudo iptables -F FORWARD
sudo stop vrc_netwatcher
sudo stop vrc_bytecounter
sudo start vrc_netwatcher
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "bash cloudsim/start_sim.bash \$1 \$2 \$3"
DELIM
chmod +x $DIR/start_sim.bash



echo "done :-)"

