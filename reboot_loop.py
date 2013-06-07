#!/usr/bin/env python

import os, sys

def wait_for_server_alive(server, router_public_ip, password):
    print( "%s waiting for %s to be alive" % (datetime.datetime.utcnow(), server) )
    found = False
    while not found:
        time.sleep(30)
        router_ssh = paramiko.SSHClient()
        try:
            router_ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            router_ssh.connect(router_public_ip, username='root', password=password)
            server_type = server.split('-')[0] # sim or fc1
            cmd = '/home/ubuntu/cloudsim/find_file_%s.bash /var/log/dpkg.log' % server_type
            stdi, stdo, stde = router_ssh.exec_command(cmd)
            out = stdo.read().strip()
            err = stde.read()
            print("%s out:%s, err:%s" % (datetime.datetime.utcnow(), out.strip(), err.strip())) 
            if out == '/var/log/dpkg.log':
                found = True
        finally:
            router_ssh.close()
            print( "%s %s alive: %s" % (datetime.datetime.utcnow(), server, found) )
            #sys.stdout.write(".")
            #sys.stdout.flush()
        
    #print( "%s %s alive: %s" % (datetime.datetime.utcnow(), server, found) )

daemon_path = os.path.abspath(os.path.join(os.path.dirname(__file__),
  'cloudsimd', 'launchers', 'launch_utils'))
sys.path.insert(0, daemon_path)

import argparse
import datetime
import time

try:
    import paramiko
except:
    print("please install paramiko:\n sudo apt-get install -y paramiko")
# from cloudsimd import launch_constellation

from softlayer import load_osrf_creds, get_machine_login_info, reboot_servers

parser = argparse.ArgumentParser(
           description=('Reboot a server in a loop'))

parser.add_argument('-s', '--server',
                    help='The server to reboot',)

parser.add_argument('-c', '--credentials_sl',
                             help='Credentials fro SoftLayer')
args = parser.parse_args()
#print(args)

server = args.server
print("server: %s" % server)

router = "router-%s" % ( server.split('-')[1])
print("router: %s" % router)

credentials_sl = args.credentials_sl
print("softlayer credentials: %s" % credentials_sl)

if not os.path.exists(credentials_sl):
    print("softlayer credentials file not found")
    exit(1)

osrf_creds = load_osrf_creds(credentials_sl)
public_ip, priv_ip, password = get_machine_login_info(osrf_creds, router)

print("router ip %s / %s pswd: %s\n\n" % (public_ip, priv_ip, password) )

count = 0
while True:
    count += 1
    print("\n\n %s ======== %s =========" % (server, count))
    wait_for_server_alive(server, public_ip, password)
    
    print( "%s %s reboot" % (datetime.datetime.utcnow(), server) )
    reboot_servers(osrf_creds, [server])
    for i in range(20):
        sys.stdout.write('.')
        sys.stdout.flush()
        time.sleep(60)
 
print ('done')

