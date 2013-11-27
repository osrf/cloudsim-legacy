#!/bin/bash

force=0
basic_auth=0
for arg in $*; do
  if [ "$arg" == "-f" ]; then
    force=1
    # Wipe out redis keys, so that we'll know later when cloudsimd is up
    redis-cli flushdb
  elif [ "$arg" == "-b" ]; then
    basic_auth=1
  else
    echo "Warning: ignoring unrecognized argument: $arg"
  fi
done


# DIR="/home/ubuntu/cloudsim"
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"


echo
echo copying data from $DIR to /var/www and /var/www-cloudsim-auth/users
echo

if [ "$basic_auth" == "1" ]; then
  sudo cp $DIR/distfiles/apache2-basic-auth.conf /etc/apache2/apache2.conf
  # create the password file if it does not exist
  sudo touch /var/www-cloudsim-auth/htpasswd
else
  sudo cp $DIR/distfiles/apache2.conf /etc/apache2/apache2.conf
fi

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

#
# create a zip of the current source tree
#
cd $DIR/..
zip -r cloudsim.zip cloudsim
sudo mv cloudsim.zip /var/www-cloudsim-auth

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
# copy version info so its accessible to the daemon
sudo cp $DIR/VERSION /var/cloudsimd

sudo cp $DIR/cloudsimd/cloudsimd.conf /etc/init
sudo initctl reload-configuration

sudo stop cloudsimd
sudo start cloudsimd

sudo apache2ctl restart

if [ "$basic_auth" == "1" ]; then
  echo ""
  echo "*******************************************************************"
  echo "Configured to use HTTP Basic Authentication.
  echo "Users in /var/www-cloudsim-auth/htpasswd must match those
  echo "in /var/www-cloudsim-auth/users."
  echo "*******************************************************************"
fi
