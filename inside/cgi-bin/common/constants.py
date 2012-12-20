# usercheck.py
EMAIL_VARNAME = 'openid.ext1.value.email'

# web.py
ADMIN_EMAIL = 'cloudsim-info@osrfoundation.org'
USER_DATABASE = '/var/www-cloudsim-auth/users'
SESSION_DATABASE = '/var/www-cloudsim-auth/sessions'
# web, logout, usercheck
OPENID_SESSION_COOKIE_NAME = 'open_id_session_id'
# web, usercheck
HTTP_COOKIE = 'HTTP_COOKIE'

BOTO_CONFIG_FILE_USEAST = '/var/www-cloudsim-auth/boto-useast'

#startup_script_builder.py
OPENVPN_CONFIG_FNAME = 'openvpn.config'
OPENVPN_STATIC_KEY_FNAME = 'static.key'
OPENVPN_CLIENT_KEY_NAME = "openvpn.key"


# warning! this is a default param but also hard coded in launchers__init__
# openvpn cloud IP
OV_SERVER_IP = '10.8.0.1'
OV_CLIENT_IP = '10.8.0.2'

OV_SIM_SERVER_IP = '10.9.0.1'
OV_SIM_CLIENT_IP = '10.9.0.2'

OV_ROBOT_SERVER_IP='10.10.0.1'
OV_ROBOT_CLIENT_IP='10.10.0.2'


ROS_SH_FNAME = "ros.sh"
MACHINES_DIR = '/var/www-cloudsim-auth/machines'
CONFIGS_DIR = "/var/cloudsimd/launchers"
TEAM_LOGIN_DISTRIBUTION= '/var/www-cloudsim-auth/cloudsim.zip'
TEAM_LOGIN_SSH_FNAME= '/var/www/cloudsim_ssh.zip'

CONSTELLATION_JSONF_NAME='constellation.json'