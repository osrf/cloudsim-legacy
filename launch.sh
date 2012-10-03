#!/bin/bash
echo name of script is $0
echo admin user $1
echo boto config $2

# cleanup
rm -rf  inside/cgi-bin/team_login_pem/

# setup admin account
echo $1 > distfiles/users

rm cloudsim.zip
zip -r cloudsim.zip .

python inside/cgi-bin/create_team_login_instance.py $2 cloudsim.zip


