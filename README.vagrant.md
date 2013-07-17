Introduction
============

We have prepared a ready to use Vagrant image for OpenStack and CloudSim to
make it easier to test and develop CloudSim without using an external cloud
provider. The included scripts setup OpenStack (Grizzly) in a virtual machine.
The virtual machine has been tested with the following requirements:

- Vagrant 1.2.4
- VirtualBox 4.2.16
- Ubuntu 12.04 as the host OS

VirtualBox
==========

This VM requires two host-only interfaces, one for the private network (i.e.
the network where the instances are launched) and another one for the public
one network (i.e. the network from which instances can be accessed from the
outside world).

You can create the two host-only interfaces with the following commands:

    :::shell
    $ VBoxManage hostonlyif create
    $ VBoxManage hostonlyif ipconfig vboxnet0 --ip 172.16.0.254 --netmask 255.255.0.0
    $ VBoxManage hostonlyif create
    $ VBoxManage hostonlyif ipconfig vboxnet1 --ip 10.10.0.1 --netmask 255.255.0.0
    
vboxnet0 and vboxnet1 will be the public and private interfaces respectively.

Usage
=====

The Vagrant image can be started by issuing the following:

    :::shell
    $ vagrant up

this command will fetch an appropiate base image (Ubuntu 12.04 x86-64) the first
time is run, unless it's not already registered within Vagrant.

After this, you should be able to access the OpenStack dashboard by pointing your
browser to http://172.16.0.201 and using the credentials for either the admin user
(username: admin, password: cloudsim) or the demo user (username: demo,
password: cloudsim).

You may use the following command to stop the Vagrant virtual machine:

    :::shell
    $ vagrant halt

The Vagrant virtual machine can be rebooted with:

    :::shell
    $ vagrant reload

And if you want to completely remove it, use the following command:

    :::shell
    $ vagrant destroy

Acknowledgements
================

The shell provisioner is based on nand2's Vagrant Devstack recipe https://github.com/nand2/vagrant-devstack
