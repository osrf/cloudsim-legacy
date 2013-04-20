#!/bin/bash

# Exit on error
set -ex
exec > ./auto_user.log 2>&1


DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR
cd $DIR

echo
echo ADDING ubuntu user with ssh_key
echo 
echo ip_address $1
echo pass $2
echo key $3

echo "create user"
echo "create user"
./create_ubuntu_user.exp $1 $2

echo "create key"
echo "create key"
./create_key.bash $DIR/$3 $1

echo "upload key"
./upload_key.exp $1 $2 $3

echo "process key"
./process_remote_ssh_key.exp  $1 $2

echo "done"
echo "-"
