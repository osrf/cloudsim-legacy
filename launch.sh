#!/bin/bash
echo name of script is $0
echo admin user $1
echo boto config $2


# setup admin account
echo $1 > distfiles/users

rm cloudsim.zip
cd ..; zip -r cloudsim/cloudsim.zip cloudsim; cd cloudsim

python inside/cgi-bin/create_team_login_instance.py $2 cloudsim.zip


