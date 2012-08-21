from __future__ import print_function
import uuid
import boto
import os
import time
import subprocess

import common

IMAGE_ID = 'ami-4438b474' # Vanilla 64-bit Ubuntu 12.04
#IMAGE_ID = 'ami-44028d74' # a custom AMI used in testing
#IMAGE_ID = 'ami-98fa58f1' # Ubuntu Server 12.04 LTS for Cluster Instances
INSTANCE_TYPE = 't1.micro' # freebie
#INSTANCE_TYPE = 'm1.small' # $0.08/hour
#INSTANCE_TYPE = 'cg1.4xlarge' # $2.10/hour; only available in us-east
# Security groups.  'openvpn' is configured to allow ssh and openvpn
SECURITY_GROUPS = ['openvpn']
# User name.  Default is 'ubuntu'
USERNAME = 'ubuntu'
# openvpn cloud IP
OV_SERVER_IP = '10.8.0.1'
# openvpn client IP
OV_CLIENT_IP = '10.8.0.2'
# Startup script
STARTUP_SCRIPT = """#!/bin/bash
apt-get update
apt-get install -y openvpn
openvpn --genkey --secret %s
cat <<DELIM > openvpn.config
dev tun
ifconfig %s %s
secret %s
DELIM
chmod 644 %s
openvpn --config openvpn.config &
"""%(common.OPENVPN_STATIC_KEY_FNAME, OV_SERVER_IP, OV_CLIENT_IP, common.OPENVPN_STATIC_KEY_FNAME, common.OPENVPN_STATIC_KEY_FNAME)

def create_ec2_instance(boto_config_file,
                        output_config_dir,
                        image_id=IMAGE_ID, 
                        instance_type=INSTANCE_TYPE,
                        security_groups=SECURITY_GROUPS,
                        username=USERNAME):

    # Load boto config from indicated file.  By overwriting boto.config,
    # our new config will be used.
    boto.config = boto.pyami.config.Config(boto_config_file)

    # No args: uses config from boto.config
    ec2 = boto.connect_ec2()

    # Create key pair to use for SSH access.  Note that 
    # create_key_pair() registers the named key with AWS.
    uid = str(uuid.uuid1())
    cfg_dir=os.path.join(output_config_dir, uid)
    if os.path.exists(cfg_dir):
        print('Directory/file %s already exists; bailing'%(cfg_dir))
        raise Exception('UUID creation did not meet expectations')
    os.makedirs(cfg_dir)
    kp_name = 'key-%s'%(uid)
    kp = ec2.create_key_pair(kp_name)
    kp_fname = os.path.join(cfg_dir, kp_name + '.pem')

    try:
        # Start it up
        res = ec2.run_instances(image_id=IMAGE_ID, key_name=kp_name, instance_type=INSTANCE_TYPE, security_groups=SECURITY_GROUPS, user_data=STARTUP_SCRIPT)
        print('Creating instance %s...'%(res.id))

        # Wait for it to boot to get an IP address
        while True:
            done = False
            for r in ec2.get_all_instances():
                if r.id == res.id and r.instances[0].public_dns_name:
                    done = True
                    break
            if done:
                break
            else:
                time.sleep(0.1)

        inst = r.instances[0]
        hostname = inst.public_dns_name

        # save the ssh key
        kp.save(cfg_dir)

        print('Waiting for sshd to respond...')
        # Wait for sshd to respond.  We check for readability of the static
        # key file because that's what we're going to scp next.
        #TODO: put a timeout in this loop
        while True:
            cmd = ['ssh', '-o', 'StrictHostKeyChecking=no', '-i', kp_fname, '%s@%s'%(USERNAME, hostname), 'ls', '/%s'%(common.OPENVPN_STATIC_KEY_FNAME)]
            po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            out,err = po.communicate()
            if po.returncode == 0:
                break
            else:
                time.sleep(0.1)

        # retrieve the openvpn key
        cmd = ['scp', '-o', 'StrictHostKeyChecking=no', '-i', kp_fname, str('%s@%s:/%s'%(USERNAME, hostname, common.OPENVPN_STATIC_KEY_FNAME)), os.path.join(cfg_dir, common.OPENVPN_STATIC_KEY_FNAME)]
        po = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out,err = po.communicate()
        if po.returncode != 0:
            raise Exception('scp failed: %s'%(err))
        # create openvpn config file
        ov_cfgfile_base = common.OPENVPN_CONFIG_FNAME
        ov_cfgfile = os.path.join(cfg_dir, ov_cfgfile_base)
        with open(ov_cfgfile, 'w') as ovcfg:
            ovcfg.write('remote %s\n'%(hostname))
            ovcfg.write('dev tun\n')
            ovcfg.write('ifconfig %s %s\n'%(OV_CLIENT_IP, OV_SERVER_IP))
            ovcfg.write('secret %s\n'%(common.OPENVPN_STATIC_KEY_FNAME))
        # print stuff out
        print('New machine created at %s.'%(hostname))
        print('Keys stored locally in %s.'%(cfg_dir))
        print('To ssh:')
        print('  ssh -i %s %s@%s'%(kp_fname, USERNAME, hostname))
        print('To connect VPN:')
        print('  cd %s'%(cfg_dir))
        print('  sudo openvpn --config %s'%(ov_cfgfile_base))
    except Exception as e:
        # Clean up
        kp.delete()
        if os.path.exists(kp_fname):
            os.unlink(kp_fname)
        os.rmdir(cfg_dir)
        raise e
