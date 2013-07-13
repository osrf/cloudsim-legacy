Introduction
============

We have prepared a ready to use Vagrant image for OpenStack and CloudSim. It
has been tested with the following:

- Vagrant 1.2.3
- OpenStack Grizzly
- Ubuntu 12.04 as the host OS

Usage
=====

The Vagrant image can be started by issuing the following:

    :::shell
    $ vagrant up

this command will fetch an appropiate base image (Ubuntu 12.04 x86-64) the first
time, in case it's not already registered within Vagrant.

You may use the following command to stop it:

    :::shell
    $ vagrant halt

The Vagrant virtual machine can be rebooted with:

    :::shell
    $ vagrant reload

And if you want to completely remove it, use the following command:

    :::shell
    $ vagrant destroy
