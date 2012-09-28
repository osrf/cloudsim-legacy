#!/bin/bash

# DIR="/home/ubuntu/cloudsim"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

sudo cp $DIR/distfiles/apache2.conf /etc/apache2/apache2.conf
sudo cp -a $DIR/* /var/www/
sudo rm -rf /var/www/distfiles
sudo chown -R www-data:www-data /var/www
sudo mkdir -p /var/www-cloudsim-auth
sudo cp $DIR/distfiles/users /var/www-cloudsim-auth/users
sudo chown -R www-data:www-data /var/www-cloudsim-auth
sudo chmod 700 /var/www-cloudsim-auth
sudo apache2ctl restart
