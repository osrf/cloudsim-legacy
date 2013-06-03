#!/bin/bash

# Run the command (from the router) in all the fc1 machines
sudo /home/ubuntu/cloudsim/vrc_ssh.py run "touch /tmp/test" fc1

# Upload the file (from the router) in all the fc1 machines
touch /tmp/test2
sudo /home/ubuntu/cloudsim/vrc_ssh.py copy /tmp/test2 /tmp fc1
rm /tmp/test2