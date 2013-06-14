#!/bin/bash

#sudo apt-get install -y python-software-properties
#sudo add-apt-repository -y ppa:w-rouesnel/openssh-hpn
#sudo apt-get update -y
#sudo apt-get install -y openssh-server

cat <<EOF >>/etc/ssh/sshd_config

# SSH HPN
HPNDisabled no
TcpRcvBufPoll yes
HPNBufferSize 8192
NoneEnabled yes
EOF

sudo service ssh restart

#sudo apt-get update
#sudo apt-get install cloudsim-client-tools

# Run the command (from the router) in all the fc1 machines
#sudo /home/ubuntu/cloudsim/vrc_ssh.py run "touch /tmp/test" fc1

# Upload the file (from the router) in all the fc1 machines
#touch /tmp/test2
#sudo /home/ubuntu/cloudsim/vrc_ssh.py copy /tmp/start_sim.bash /home/ubuntu/cloudsim sim
#rm /tmp/test2
