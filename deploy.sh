#!/bin/bash

# DIR="/home/ubuntu/cloudsim"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

cd $DIR
hg log -l5 > hg_log.txt

echo
echo copying data from $DIR to /var/www and /var/www-cloudsim-auth/users
echo

sudo cp $DIR/distfiles/apache2.conf /etc/apache2/apache2.conf

sudo rm -rf /var/cloudsimd
sudo mkdir -rf /var/cloudsimd

sudo rm -rf /var/www
sudo mkdir /var/www

sudo cp -a $DIR/* /var/www/
sudo rm -rf /var/www/distfiles
sudo chown -R www-data:www-data /var/www
sudo mkdir -p /var/www-cloudsim-auth/machines

if [ -f $DIR/boto-useast ]
then
    sudo mv -f $DIR/boto-useast /var/www-cloudsim-auth
fi

cd $DIR/..
zip -r cloudsim.zip cloudsim
sudo mv -f cloudsim.zip /var/www-cloudsim-auth
cd $DIR
 

if [ ! -f /var/www-cloudsim-auth/users ]
then
   sudo cp $DIR/distfiles/users /var/www-cloudsim-auth/users
fi


 

sudo chown -R www-data:www-data /var/www-cloudsim-auth
sudo chmod 700 /var/www-cloudsim-auth

#
# Setup a daemons to launch and monitor simulations for us
#
sudo cp $DIR/cloudsimd/cloudsimd.conf /etc/init
sudo cp $DIR/cloudsimd/cloudsim_monitord.conf /etc/init

sudo rm -rf /var/cloudsimd
sudo mkdir -p /var/cloudsimd
sudo cp -a $DIR/cloudsimd/* /var/cloudsimd

sudo cp -a $DIR/inside/cgi-bin/common /var/cloudsimd

sudo initctl reload-configuration
sudo stop cloudsimd
sudo stop cloudsim_monitord

sudo start cloudsimd
sudo start cloudsim_monitord


sudo apache2ctl restart
