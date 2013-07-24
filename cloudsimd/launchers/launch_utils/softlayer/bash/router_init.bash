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
sed "s/^address 10\..*/address \$new_ip/" \$file.bak > \$file

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

# --------------------------------------------

cat <<DELIM > $DIR/ping_gazebo.bash
#!/bin/bash
ssh -t -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP ". /usr/share/drcsim/setup.sh; timeout -k 1 5 gztopic list"
DELIM
chmod +x $DIR/ping_gazebo.bash

# --------------------------------------------
cat <<DELIM > $DIR/ping_gl.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "DISPLAY=localhost:0 timeout -k 1 5 glxinfo"
DELIM
chmod +x $DIR/ping_gl.bash

# --------------------------------------------

cat <<DELIM > $DIR/stop_sim.bash
#!/bin/bash
sudo stop vrc_netwatcher
kill -9 \$(ps aux | grep vrc_netwatcher | awk '{print \$2}') || true
sudo stop vrc_bytecounter
sudo redis-cli set vrc_target_outbound_latency 0
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "bash cloudsim/stop_sim.bash"
sudo iptables -F FORWARD

# Stop the latency injection
sudo stop vrc_controller_private
sudo stop vrc_controller_public

# Restore the default tc rules
sudo vrc_init_tc.py bond0
sudo vrc_init_tc.py bond1
DELIM
chmod +x $DIR/stop_sim.bash

# --------------------------------------------

cat <<DELIM > $DIR/start_sim.bash
#!/bin/bash

# Just rename the old network usage file
sudo mv /tmp/vrc_netwatcher_usage.log /tmp/vrc_netwatcher_usage_\`date | tr -d ' '\`.log || true

# Stop the latency injection
sudo stop vrc_controller_private
sudo stop vrc_controller_public

# Restore the default tc rules
sudo vrc_init_tc.py bond0
sudo vrc_init_tc.py bond1

sudo iptables -F FORWARD
sudo stop vrc_netwatcher
kill -9 \$(ps aux | grep vrc_netwatcher | awk '{print \$2}') || true
sudo stop vrc_bytecounter
sudo start vrc_netwatcher
if ! ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "nohup bash cloudsim/start_sim.bash \$1 \$2 \$3 > ssh_start_sim.out 2> ssh_start_sim.err < /dev/null"; then
  echo "[router start_sim.bash] simulator start_sim.bash returned non-zero"
  exit 1
fi

DELIM
chmod +x $DIR/start_sim.bash

# --------------------------------------------

cat <<DELIM > $DIR/set_vrc_private.bash
#!/bin/bash

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "set_vrc_private.sh"

DELIM
chmod +x $DIR/set_vrc_private.bash

# --------------------------------------------

cat <<DELIM > $DIR/copy_net_usage.bash
#!/bin/bash

# 1. Copy the directory containing the JSON task file and the network usage to the simulator
# 2. Run a script on the simulator that zip all the log files and send them to the portal
USAGE="Usage: copy_net_usage <task_dirname> <zipname>"

if [ \$# -ne 2 ]; then
  echo \$USAGE
  exit 1
fi

echo --- >> copy_net_usage.log 2>&1

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@10.0.0.51 mkdir -p /home/ubuntu/cloudsim/logs >> copy_net_usage.log 2>&1

TASK_DIRNAME=\$1
if [ -f /tmp/vrc_netwatcher_usage.log ];
then
  cp /tmp/vrc_netwatcher_usage.log \$TASK_DIRNAME >> copy_net_usage.log 2>&1
fi
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem -r /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME ubuntu@10.0.0.51:/home/ubuntu/cloudsim/logs/ >> copy_net_usage.log 2>&1

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@10.0.0.51 bash /home/ubuntu/cloudsim/send_to_portal.bash \$1 \$2 /home/ubuntu/ubuntu-portal.key vrcportal-test.osrfoundation.org >> copy_net_usage.log 2>&1
DELIM
chmod +x $DIR/copy_net_usage.bash

# --------------------------------------------

cat <<DELIM > $DIR/get_sim_logs.bash
#!/bin/bash

# Get state.log and score.log from the simulator 

USAGE="Usage: get_sim_logs.bash <task_dirname>"

if [ \$# -ne 1 ]; then
  echo \$USAGE
  exit 1
fi

TASK_DIRNAME=\$1

mkdir -p /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME

# Copy the log files
scp -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i /home/ubuntu/cloudsim/key-sim.pem ubuntu@10.0.0.51:/tmp/\$TASK_DIRNAME/* /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME || true

# Copy the network usage
if [ -f /tmp/vrc_netwatcher_usage.log ];
then
  cp /tmp/vrc_netwatcher_usage.log /home/ubuntu/cloudsim/logs/\$TASK_DIRNAME >> copy_net_usage.log 2>&1
fi

DELIM
chmod +x $DIR/get_sim_logs.bash

# --------------------------------------------


cat <<DELIM > $DIR/update_constellation.bash
#!/bin/bash
set -ex
exec > $DIR/update_constellation.log 2>&1

echo "TODO: update_drcsim.bash"

ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "nohup sudo cloudsim/update_software.bash > update_software_sim.out 2> update_software_sim.err < /dev/null"
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc1.pem ubuntu@$FC1_IP "nohup sudo cloudsim/update_software.bash > update_software_fc1.out 2> update_software_fc1.err < /dev/null"
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-fc2.pem ubuntu@$FC2_IP "nohup sudo cloudsim/update_software.bash > update_software_fc2.out 2> update_software_fc2.err < /dev/null"

# update local packages on the router
sudo cloudsim/update_drcsim.bash &

DELIM
chmod +x $DIR/update_constellation.bash

echo "done :-)"
