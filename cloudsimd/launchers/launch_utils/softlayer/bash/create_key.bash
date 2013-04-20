#/bin/bash

echo key name: $1 
echo ip $2

ssh-keygen -f /var/www/.ssh/known_hosts -R $2
ssh-keygen -q -t rsa -f $1.pem -N ""



