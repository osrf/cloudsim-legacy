from __future__ import print_function

import os
import time
from fabric.api import run, cd, sudo, put, local, env
import getpass
from launch_db import LaunchException
from launch_db import log_msg

# import paramiko
# ssh = paramiko.SSHClient()
# ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
# privkey = paramiko.RSAKey.from_private_key_file('xxx.pem')
# ssh.connect('xxx.compute-1.amazonaws.com', username='ubuntu', pkey=privkey)
# stdin, stdout, stderr = ssh.exec_command("nohup ssh  -f -o StrictHostKeyChecking=no -i     ~/.ssh/xxx.pem ubuntu@xxx.compute-1.amazonaws.com -L 16646:localhost:16646 -L -N >& /dev/null < /dev/null &")
# ssh.close()

def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def wait_for_ssh(count, sleep, ip, ssh_key_fname):
    """
    Loops until a remote cmd can be executed by fabric on the machine's ip
    """
    env.host_string = ip
    env.user = 'ubuntu'
    env.key_filename = ssh_key_fname

    done = False
    while not done:
        time.sleep(sleep)
        count -= 1
        if count < 0:
            raise LaunchException('Timeout while waiting for ssh')
        try:
            sudo('pwd')
            done = True
        except:
            pass


def install_requirements(ip, ssh_key_fname):
    """
    todo
    """

    # tell fabric where to connect
    env.host_string = ip
    env.user = 'ubuntu'
    env.key_filename = ssh_key_fname

    sudo('pwd')
    output = run('grep DISTRIB_CODENAME /etc/lsb-release')
    _, release = output.split('=')
    url = 'http://apt.puppetlabs.com/puppetlabs-release-%s.deb' % release

    with cd('/tmp'):
        run('wget -O puppetlabs-release-%s.deb %s' % (release, url))
        sudo('dpkg -i puppetlabs-release-%s.deb' % release)

    sudo('apt-get update')

    sudo('apt-get -y install puppet-common puppet ruby1.9 ruby-odbc')


def provision(constellation_directory, ip, ssh_key_fname, configuration):
    """
    todo
    """
    # tell fabric where to connect
    env.host_string = ip
    env.user = 'ubuntu'
    env.key_filename = ssh_key_fname

    parent_dir = os.path.abspath(os.path.dirname(__file__))
    local_path = os.path.join(parent_dir, 'puppet', 'Puppetfile')
    put(local_path=local_path, remote_path='/etc/puppet', use_sudo=True)
    librarian_installed = False if run('gem search -i librarian-puppet',
                                       quiet=True) == 'false' else True
    if librarian_installed:
        sudo('yes Y|gem uninstall librarian-puppet')

    librarian_maestrodev_installed = False if run('gem search -i '
            'librarian-puppet-maestrodev', quiet=True) == 'false' else True

    if not librarian_maestrodev_installed:
        sudo('gem install librarian-puppet-maestrodev')  # y
        with cd('/etc/puppet'):
            sudo('librarian-puppet install --clean')  # y
    else:
        with cd('/etc/puppet'):
            sudo('librarian-puppet update') 

    timestamp = int(time.time())
    username = getpass.getuser()
    puppet_bundle = 'puppet-bundle-%s-%d' % (username, timestamp)

    # switch to the directory containing the puppet dir, so that the tar
    # command works as expected
    src_bundle_full_path = os.path.join(constellation_directory,
                                    "%s.tar.gz" % puppet_bundle)
    os.chdir(parent_dir)
    local("tar --transform 's,^,%s/,S' -czf %s puppet/*" % (
                                                    puppet_bundle,
                                                    src_bundle_full_path))
    put(src_bundle_full_path, '.')
    run('tar xzf %s.tar.gz' % puppet_bundle)

    the_host = ip
    cmd = 'FACTER_fqdn=%s puppet apply --verbose --debug ' \
         '--modulepath=/etc/puppet/modules:/usr/share/puppet/modules:' \
         '%s/puppet/modules %s/puppet/manifests/site.pp' % (the_host,
         puppet_bundle, puppet_bundle)
    log(cmd)
    sudo(cmd)
