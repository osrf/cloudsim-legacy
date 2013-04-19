#!/bin/bash

echo ip_address $1
echo pass $2
echo key $3

./create_key.bash $3
./create_ubuntu_user.exp $1 $2
./upload_key.exp $1 $2 $3
./process_remote_ssh_key.exp  $1 $2

