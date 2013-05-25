#!/bin/bash

# Exit on error
set -ex
exec > ./auto_user_$1.log 2>&1

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
echo $DIR
cd $DIR

echo
echo ADDING ubuntu user with ssh_key
echo 
echo ip_address $1
echo pass $2
echo key $3
echo "*********"

./create_ubuntu_user.exp $1 $2
./upload_key.exp $1 $2 $3
./process_remote_ssh_key.exp  $1 $2

echo "done"
echo "-"
