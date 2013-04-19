#/bin/bash

echo key name: $1 

ssh-keygen -q -t rsa -f ./$1.pem -N ""



