#!/bin/bash

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR
echo
echo ADDING ubuntu user with ssh_key
echo 
echo ip_address $1
echo pass $2
echo key $3

echo "create key"
$DIR/create_key.bash $3
echo "create user"
$DIR/create_ubuntu_user.exp $1 $2
echo "upload key"
$DIR/upload_key.exp $1 $2 $3
echo "process key"
$DIR/process_remote_ssh_key.exp  $1 $2
echo "done"

