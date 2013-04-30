#!/bin/bash

set -ex
exec > router_init.log 2>&1

# DIR=/home/ubuntu/cloudsim

DIR=$1
SIM_IP=$2
FC1_IP=$3
FC2_IP=$4


sudo apt-get install -y expect


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
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP ". /usr/share/drcsim/setup.sh; timeout 5 gztopic list"
DELIM
chmod +x $DIR/ping_gazebo.bash


cat <<DELIM > $DIR/ping_gl.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "DISPLAY=localhost:0 timeout 5 glxinfo"
DELIM
chmod +x $DIR/ping_gl.bash


cat <<DELIM > $DIR/stop_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "killall -INT roslaunch"
DELIM
chmod +x $DIR/stop_sim.bash


cat <<DELIM > $DIR/start_sim.bash
#!/bin/bash
ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -i $DIR/key-sim.pem ubuntu@$SIM_IP "bash cloudsim/start_sim.bash \$1 \$2 \$"
DELIM
chmod +x $DIR/start_sim.bash



echo "done :-)"

