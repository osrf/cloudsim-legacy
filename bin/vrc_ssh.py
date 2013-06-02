#!/usr/bin/env python

"""
Program that runs a script or copy a file into a set of machines.
"""

import argparse
import os
import sys
from threading import Thread
import abc
import subprocess
import getpass
import Queue

NORMAL = '\033[00m'
RED = '\033[0;31m'
CLOUDSIM_PREFIX = 'OSRF_CloudSim_'
CONST_PREFIX = 'OSRF_VRC_Constellation_'
MACHINES = ['cs', 'router', 'sim', 'fc1', 'fc2']


class Ssh_base(object):
    '''
    Abstract class for running a ssh/scp command.
    '''
    DEFAULT_SSH_OPTS = ('-o UserKnownHostsFile=/dev/null '
                        '-o StrictHostKeyChecking=no '
                        '-o ConnectTimeout=5')
    __metaclass__ = abc.ABCMeta

    def __init__(self, name, constellation=None):
        self.constellation = constellation
        self.name = name

    def get_credentials(self):
        '''
        To be implemented by derived classes.
        '''
        return

    def run_remote_command(self, cmd, queue):
        '''
        Execute a command, and put in a shared queue the stdout, stderr outputs.
        @param cmd Command to be executed
        @param queue Shared queue (thread safe)
        '''
        po = subprocess.Popen(cmd.split(), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        out, err = po.communicate()
        if po.returncode == 0:
            msg = self.name + ': Success'
            if out != '':
                msg += '\n\t' + out.replace('\n', '\n\t')
            queue.put(msg)
        else:
            queue.put(self.name + ': Error\n\t%s' % err)

    def get_cmd_context(self, ssh_options):
        '''
        Returns the current ssh options, key file and ip of the current machine.
        @param ssh_options Extra ssh options to be used
        '''
        ssh_options = Ssh_base.DEFAULT_SSH_OPTS + ssh_options
        key, ip = self.get_credentials()

        if not os.path.exists(key):
            raise NameError('Identity file not found (%s)...Aborting' % key)

        return ssh_options, key, ip

    def copy(self, ssh_options, src, user, dst, queue):
        '''
        Copy a file into a remote machine.
        @param ssh_options Extra ssh options
        @param src Full path to the file to be uploaded
        @param user Remote user used by ssh
        @param dst Destination path
        @param queue Shared queue to store the output of the command
        '''
        ssh_options, key, ip = self.get_cmd_context(ssh_options)
        cmd = ('scp ' + ssh_options + ' -i ' + key + ' ' + src + ' ' +
               user + '@' + ip + ':' + dst)
        self.run_remote_command(cmd, queue)

    def run(self, ssh_options, cmd, user, queue):
        '''
        Run a command in a remote machine.
        @param ssh_options Extra ssh options
        @param cmd Command to be executed
        @param user Remote user used by ssh
        @param queue Shared queue to store the output of the command
        '''
        ssh_options, key, ip = self.get_cmd_context(ssh_options)
        cmd = ('ssh ' + ssh_options + ' -i ' + key + ' ' +
               user + '@' + ip + ' ' + cmd)
        self.run_remote_command(cmd, queue)


class Ssh_cloudsim(Ssh_base):
    '''
    Derived class for running a ssh/scp command in a CloudSim machine.
    '''
    def __init__(self, name, constellation):
        super(Ssh_cloudsim, self).__init__(name, constellation)

    def get_credentials(self):
        '''
        Return the CloudSim credentials.
        '''
        directory = self.constellation['constellation_directory']
        ip = self.constellation['simulation_ip']
        key = os.path.join(directory, 'cs', 'key-cs.pem')
        return (key, ip)


class Ssh_router(Ssh_base):
    '''
    Derived class for running a ssh/scp command in a router machine.
    '''
    def __init__(self, name, constellation):
        super(Ssh_router, self).__init__(name, constellation)

    def get_credentials(self):
        '''
        Return the Router credentials.
        '''
        directory = self.constellation['constellation_directory']
        ip = self.constellation['router_public_ip']
        key = os.path.join(directory, 'router', 'key-router.pem')
        return (key, ip)


class Ssh_machine(Ssh_base):
    '''
    Derived class for running a ssh/scp command in a sim, fc1, or fc2 machine.
    '''
    def __init__(self, machine_type):
        super(Ssh_machine, self).__init__(machine_type)
        if machine_type not in ['sim', 'fc1', 'fc2']:
            raise NameError('Invalid machine type: %s' % machine_type)
        else:
            self.machine_type = machine_type

    def get_credentials(self):
        '''
        Return the Sim, FC1, or FC2 credentials.
        '''
        if self.machine_type == 'sim':
            ip = '10.0.0.51'
            key_name = 'key-sim.pem'
        elif self.machine_type == 'fc1':
            ip = '10.0.0.52'
            key_name = 'key-fc1.pem'
        elif self.machine_type == 'fc2':
            ip = '10.0.0.53'
            key_name = 'key-fc2.pem'
        else:
            raise NameError('Invalid machine type: %s' % self.machine_type)

        key = os.path.join('/home/ubuntu/cloudsim', key_name)
        return (key, ip)


def go(args):
    '''
    Function that run a command or copy a file in multiples machines. A thread
    is created to the job in every machine. A shared queue among the threads
    is used to capture the returned value of the commands, stdout, and stderr.
    @param args Command line arguments
    '''

    # Retrieve command line arguments
    ssh_options = args.ssh_options
    machine_type = args.type
    subcommand = args.which
    if subcommand == 'run':
        arg = args.cmd
        stats_msg = 'Command executed in'
    elif subcommand == 'copy':
        arg = args.src
        dst = args.dst
        stats_msg = 'File uploaded into'

        if not os.path.exists(arg):
            print '%sFile not found: (%s)...Aborting%s' % (RED, arg, NORMAL)
            sys.exit(1)

    else:
        print 'Invalid subcommand (%s)...Aborting' % subcommand
        sys.exit(1)

    # Sanity check
    if getpass.getuser() != 'root':
        print "Invalid user, you should run this program as root...Aborting"
        sys.exit(1)

    # Counter for stats, threads for the job, and a queue for the returned vals11
    counter = 0
    threads = []
    succeed_queue = Queue.Queue()

    if machine_type in ['cs', 'router']:
        try:
            # Import cloudsimd
            basepath = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            if not os.path.exists(os.path.join(basepath, 'cloudsimd')):
                print 'Your DB does not contain any remote CloudSim...Aborting'
                sys.exit(1)
            sys.path.insert(0, basepath)
            from cloudsimd import cloudsimd

            const_list = cloudsimd.list_constellations()
        except Exception, excep:
            print ('%sError importing cloudsimd: %s%s'
                   % (RED, repr(excep), NORMAL))
            sys.exit(1)

        # Iterate over the list of CloudSims
        for constellation in const_list:
            try:
                name = constellation['constellation_name']

                if name.startswith(CLOUDSIM_PREFIX) and machine_type == 'cs':
                    machine = Ssh_cloudsim(name, constellation)
                elif name.startswith(CONST_PREFIX) and machine_type == 'router':
                    machine = Ssh_router(name, constellation)
                else:
                    continue

                if subcommand == 'run':
                    params = [ssh_options, arg, 'ubuntu', succeed_queue]
                    t = Thread(target=machine.run, args=params)
                elif subcommand == 'copy':
                    params = [ssh_options, arg, 'ubuntu', dst, succeed_queue]
                    t = Thread(target=machine.copy, args=params)

                threads.append(t)
                t.start()

                counter += 1
            except Exception, excep:
                print ('%sError running command: %s%s'
                       % (RED, repr(excep), NORMAL))
                counter -= 1

    elif machine_type in ['sim', 'fc1', 'fc2']:
        try:
            machine = Ssh_machine(machine_type)
            if subcommand == 'run':
                machine.run(ssh_options, arg, 'ubuntu', succeed_queue)
            elif subcommand == 'copy':
                machine.copy(ssh_options, arg, 'ubuntu', dst, succeed_queue)

            counter += 1
        except Exception, excep:
            print repr(excep)
            sys.exit(1)
    else:
        print 'Invalid machine type (%s)...Aborting' % machine_type
        sys.exit(1)

    # Wait for all the threads to finish
    [x.join() for x in threads]

    # Print some stats
    for elem in sorted(list(succeed_queue.queue)):
        print elem
    print '%s %d machine/s' % (stats_msg, counter)


if __name__ == '__main__':

    # Specify top level command line arguments
    parser = argparse.ArgumentParser(description='Manage multiple VRC SSH/SCP')
    parser.add_argument('-o', '--ssh_options', default='', help='ssh options')
    subparsers = parser.add_subparsers(title='subcommands',
                                       description='valid subcommands',
                                       help='additional help')

    # create the parser for the "run" command
    parser_run = subparsers.add_parser('run',
                                       help='Run a command in several machines')
    parser_run.add_argument('cmd', help='Command to run remotely')
    parser_run.set_defaults(which='run')
    parser_run.add_argument('type', choices=MACHINES, help='Remote machine type')
    parser_run.set_defaults(func=go)

    # create the parser for the "copy" command
    parser_copy = subparsers.add_parser('copy',
                                        help='Copy a file into several machines')
    parser_copy.add_argument('src', help='File to upload')
    parser_copy.set_defaults(which='copy')
    parser_copy.add_argument('dst', help='Destination path')
    parser_copy.add_argument('type', choices=MACHINES, help='Remote machine type')
    parser_copy.set_defaults(func=go)

    # Parse command line arguments
    args = parser.parse_args()
    args.func(args)
