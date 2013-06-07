#!/bin/bash

if [ "$1" == "-f" ]; then
  force=1
  # Wipe out redis keys, so that we'll know later when cloudsimd is up
  redis-cli flushdb
else
  force=0
fi


# DIR="/home/ubuntu/cloudsim"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


echo
echo copying data from $DIR to /var/www and /var/www-cloudsim-auth/users
echo

sudo cp $DIR/distfiles/apache2.conf /etc/apache2/apache2.conf

sudo rm -rf /var/www
sudo mkdir -p /var/www

#
# Copy dev files to website directory
#
sudo cp -a $DIR/* /var/www/
sudo find /var/www -name "*.pyc" -exec rm {} \;

#
# Change owner of CloudSim files for security: 
#
sudo rm -rf /var/www/distfiles
sudo chown -R www-data:www-data /var/www
sudo mkdir -p /var/www-cloudsim-auth/machines

#
# copy cloud credentials
#
sudo cp -f $DIR/../boto.ini /var/www-cloudsim-auth/boto-useast
sudo cp -f $DIR/../softlayer.json /var/www-cloudsim-auth/softlayer.json 
sudo cp -f $DIR/../cloudsim_portal.key /var/www-cloudsim-auth/cloudsim_portal.key
sudo cp -f $DIR/../cloudsim_bitbucket.key /var/www-cloudsim-auth/cloudsim_bitbucket.key

cd $DIR/..
zip -r cloudsim.zip cloudsim
sudo mv -f cloudsim.zip /var/www-cloudsim-auth
cd $DIR

if sudo test ! -f /var/www-cloudsim-auth/cloudsim_portal.json -o $force -eq 1
then
   sudo cp $DIR/../cloudsim_portal.json /var/www-cloudsim-auth/cloudsim_portal.json
fi


if sudo test ! -f /var/www-cloudsim-auth/users -o $force -eq 1
then
   sudo cp $DIR/distfiles/users /var/www-cloudsim-auth/users
fi

sudo chown -R www-data:www-data /var/www-cloudsim-auth
sudo chmod 704 /var/www-cloudsim-auth

#
# Setup a daemons to launch and monitor simulations for us
#
sudo rm -rf /var/cloudsimd
sudo mkdir -p /var/cloudsimd
sudo cp -a $DIR/cloudsimd/* /var/cloudsimd


sudo cp $DIR/cloudsimd/cloudsimd.conf /etc/init
sudo initctl reload-configuration

sudo stop cloudsimd
sudo start cloudsimd

sudo apache2ctl restart
