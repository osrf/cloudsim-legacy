#!/bin/bash


#
#
# Do you have expect-dev installed?
#

IP=50.97.149.36
PASS=UuS8erVm
KEY=key-router-01

rm $KEY*
./auto_ubuntu.bash $IP $PASS $KEY
ssh -i $KEY.pem ubuntu@$IP

# ifconfig eth4 10.0.0.51 netmask 255.255.255.0 

