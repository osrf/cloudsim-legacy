#!/usr/bin/env python
# -*- coding: iso-8859-15 -*-

"""
Checks running instances in the cloud to prevent machine leaks.

@author: Carlos Agüero (caguero@osrfoundation.org)
"""

import argparse
from boto.ec2.connection import EC2Connection
import time
import smtplib
from email.mime.text import MIMEText
import yaml
import sys
import re

def mail(gmail_user, gmail_pwd, to, subject, text):
    '''
    Send email using a gmail account.

    @param gmail_user: gmail email
    @param gmail_pwd: gmail password
    @param to: destination email
    @param subject: email's subject
    @param text: email's body message
    '''
    msg = MIMEText(text)
    msg['Subject'] = subject
    msg['From'] = gmail_user
    msg['To'] = to

    mailServer = smtplib.SMTP("smtp.gmail.com", 587)
    mailServer.ehlo()
    mailServer.starttls()
    mailServer.ehlo()
    mailServer.login(gmail_user, gmail_pwd)
    mailServer.sendmail(gmail_user, [to], msg.as_string())
    mailServer.quit()


def notify(notifications, gmail_user, gmail_passwd, max_hours):
    '''
    Notify alarms to the owners of the instances (or admin in any other case).

    @param notifications: Dictionary where the keys are usernames and values
                          contain inform. to be notified (instance_id, ...)
    @param gmail_user: gmail account used to send alarms
    @param gmail_passwd: gmail password
    @param max_hours: the notification contains the current limit (a num of
                      hours) for each running instance
    '''
    subject = 'CloudSim warning: possible instance leak'
    for username in notifications:
        msg = ''
        for instance in notifications[username]:
            account = instance[0]
            httptarget = instance[1]
            instance = instance[2]
            httplink = 'Suspicious instance ' + instance + \
                       ' running for long time ( >' + str(max_hours) + \
                       ' hours) in '
            httplink += account + ' account (' + httptarget + ')\n'

            msg += httplink

        msg += '\n\nhttp://internal.osrfoundation.org'

        # ***** REMOVE THIS WHEN THE SCRIPT IS READY *****
        # username = 'caguero@osrfoundation.org'
        # ***** ------------------------------------ *****

        print 'Sending alarm to ', username
        mail(gmail_user, gmail_passwd, username, subject, msg)


def go(configuration, admin_email, max_hours, gmail_user, gmail_passwd):
    '''
    Use a YAML file with a list of AWS accounts and check possible machine
    leaks. If an instance is running for more than a given threshold
    (given in hours), an email notification is sent to the instance's owners
    or to the admin email account (if the owner info is not available).
    In addition, it is possible to specify in the config file an extra set
    of email accounts for each AWS account. It is also possible to
    waive an instance if its name matches a given prefix specified in the
    conf file.

    @param configuration: Dictionary loaded from the YAML file
    @param admin_email: admin email to notify instances with unknown owners
    @param max_hours: Max. number of hours allowed before send an alarm
    @param gmail_user: gmail account to send alarm messages
    @param gmail_passwd: gmail password
    '''
    notifs = {}

    for account in configuration:

        # Read main atributes of the AWS account
        account_name = account['name']
        key = account['key']
        secret = account['secret']
        console = account['console']
        notifyTo = account['notifyTo']
        excluded_prefix = account['excluded-prefix-iname']
        print 'Checking ', account_name, 'account'

        ec2conn = EC2Connection(key, secret)
        reservations = ec2conn.get_all_instances()
        instances = [i for r in reservations for i in r.instances]

        for i in instances:
            # Check if the instance is running and not excluded
            # in the configuration file
            if i.state == 'running':
                is_excluded = False
                for prefix in excluded_prefix:
                    if 'Name' in i.tags and i.tags['Name'].startswith(prefix):
                        is_excluded = True

                if not is_excluded:
                    # The instances use GMT time. The local time is
                    # converted to GMT. Both are converted to seconds
                    # and the difference is calculated
                    start = time.strptime(i.launch_time[:19],
                                          '%Y-%m-%dT%H:%M:%S')
                    ins_start = time.mktime(start)
                    now = time.mktime(time.gmtime(time.time()))
                    diff = float(now - ins_start)

                    # -1h. for the tm_isdst attribute (is set to -1 ??)
                    diff -= 3600

                    # Calculate hours and minutes (format is h.00 to h.99)
                    minute = diff / 60
                    hr = minute / 60

                    # Is the number of running hours above the threshold?
                    if hr > max_hours:

                        # Retrieve the instance's owner (or admin)
                        username = admin_email
                        if 'username' in i.tags:
                            username = i.tags['username']

                        # Retrieve the instance's name if possible
                        instance_name = 'unknown'
                        if 'Name' in i.tags:
                            instance_name = i.tags['Name']

                        # Update a dict. with the future notifications.
                        # The keys are the email accounts and the value
                        # are the data to be included in the notification.
                        # Email accounts are unique.
                        for user in list(set(notifyTo + [username])):
                            if user in notifs:
                                notifs[user].append((account_name, console,
                                                     instance_name))
                            else:
                                notifs[user] = [(account_name, console,
                                                instance_name)]
    # Check if the email address is valid
    if re.match(r"[^@]+@[^@]+\.[^@]+", account_name):
        notify(notifs, gmail_user, gmail_passwd, max_hours)


if __name__ == "__main__":

    try:
        # Specify command line arguments
        parser = argparse.ArgumentParser(description='Checks running instances in \
                                                      the cloud to prevent \
                                                      machine leaks.')
        parser.add_argument('file', metavar='CONF-FILE',
                            help='YAML file with the accounts information')
        parser.add_argument('admin_email', metavar='ADMIN-EMAIL',
                            help='email to notify unknown instances')
        parser.add_argument('max_hours', metavar='MAX-HOURS', type=int,
                            help='max. hours allowed for a running instance')
        parser.add_argument('gmail_user', metavar='GMAIL-USER',
                            help='gmail account for sending alarms')
        parser.add_argument('gmail_passwd', metavar='GMAIL-PASSWD',
                            help='gmail password for sending alarms')
        args = parser.parse_args()
        conf_file = args.file
        admin_email = args.admin_email
        max_hours = args.max_hours
        gmail_user = args.gmail_user
        gmail_passwd = args.gmail_passwd

        # Load YAML conf file with the accounts information to check
        f = open(conf_file)
        configuration = yaml.load_all(f)

        # Check the accounts!
        go(configuration, admin_email, max_hours, gmail_user, gmail_passwd)
        f.close()
        sys.exit(0)
    except Exception, ex:
        print 'Exception captured: ', ex
        sys.exit(1)
