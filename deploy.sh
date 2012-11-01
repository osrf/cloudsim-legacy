#!/bin/bash

# DIR="/home/ubuntu/cloudsim"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

echo
echo copying data from $DIR to /var/www and /var/www-cloudsim-auth/users
echo

sudo cp $DIR/distfiles/apache2.conf /etc/apache2/apache2.conf

sudo cp -a $DIR/* /var/www/
sudo rm -rf /var/www/distfiles
sudo chown -R www-data:www-data /var/www
sudo mkdir -p /var/www-cloudsim-auth

if [ ! -f $DIR/distfiles/users ];
then
   echo creating a new users file
   sudo cp $DIR/distfiles/users /var/www-cloudsim-auth/users
else
   echo preserving existing users file
fi

 

sudo chown -R www-data:www-data /var/www-cloudsim-auth
sudo chmod 700 /var/www-cloudsim-auth

#
# Setup a daemon to launch simulations for us
#
sudo cp $DIR/cloudsimd/cloudsimd.conf /etc/init
sudo mkdir -p /var/cloudsimd
sudo cp -a $DIR/cloudsimd/* /var/cloudsimd
sudo cp -a $DIR/inside/cgi-bin/common /var/cloudsimd

sudo initctl reload-configuration
sudo stop cloudsimd
sudo start cloudsimd

sudo apache2ctl restart
