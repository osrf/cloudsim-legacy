from __future__ import print_function

import time
import boto
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.connection import EC2Connection
from boto.vpc import VPCConnection
from boto.pyami.config import Config as BotoConfig

from launch_db import get_cloudsim_config
from launch_db import log_msg
from launch_db import ConstellationState
from sshclient import clean_local_ssh_key_entry
import shutil
import os


VPN_PRIVATE_SUBNET = '10.0.0.0/24'
OPENVPN_CLIENT_IP = '11.8.0.2'


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


class LaunchException(Exception):
    pass


def acquire_aws_server(constellation_name,
                       credentials_ec2,
                       constellation_directory,
                       machine_prefix,
                       startup_script,
                       tags):

    sim_machine_name = "%s_%s" % (machine_prefix, constellation_name)
    sim_key_pair_name = 'key-%s-%s' % (machine_prefix, constellation_name)
    ec2conn = aws_connect()[0]
    availability_zone = boto.config.get('Boto', 'ec2_region_name')
    constellation = ConstellationState(constellation_name)

    constellation.set_value('simulation_launch_msg',
                            "setting up security groups")
    sim_sg_name = 'sim-sg-%s' % (constellation_name)
    log("Creating a security group")
    sim_security_group = ec2conn.create_security_group(sim_sg_name,
        "simulator security group for constellation %s" % constellation_name)
    sim_security_group.authorize('tcp', 80, 80, '0.0.0.0/0')   # web
    sim_security_group.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
    sim_security_group.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
    sim_security_group_id = sim_security_group.name
    log("Security group created")
    constellation.set_value('sim_security_group_id', sim_security_group_id)

    constellation.set_value('simulation_launch_msg', "creating ssh keys")
    constellation.set_value('sim_key_pair_name', sim_key_pair_name)
    key_pair = ec2conn.create_key_pair(sim_key_pair_name)
    key_pair.save(constellation_directory)
    amis = _get_amazon_amis(availability_zone)
    aws_image = amis['ubuntu_1204_x64']

    roles_to_reservations = {}

    if availability_zone.startswith('nova'):
        instance_type = 'cloudsim-basic'
    else:
        instance_type = 't1.micro'
    try:
        constellation.set_value('simulation_launch_msg', "requesting machine")
        res = ec2conn.run_instances(image_id=aws_image,
            instance_type=instance_type,
            #subnet_id      = subnet_id,
            #private_ip_address=SIM_IP,
            security_groups=[sim_security_group_id],
            key_name=sim_key_pair_name,
            user_data=startup_script)
        roles_to_reservations['simulation_state'] = res.id
    except Exception as e:
        constellation.set_value("error", "%s" % e)
        raise

    print ("\n##############################################")
    print ("# Your CloudSim instance has been launched.  #")
    print ("# It will take around 5-10 mins to be ready. #")
    print ("# Your CloudSim's URL will appear here soon. #")
    print ("#                Stay tuned!                 #")
    print ("##############################################\n")

    # running_machines = wait_for_multiple_machines_to_run(ec2conn,
    # roles_to_reservations, constellation, max_retries = 150
    # final_state = 'network_setup')

    running_machines = {}
    count = 200
    done = False

    while not done:
        log("attempt %s" % count)
        time.sleep(2)
        count -= 1
        for r in ec2conn.get_all_instances():
            if count < 0:
                msg = ("timeout while waiting "
                       "for EC2 machine(s) %s" % sim_machine_name)
                raise LaunchException(msg)
            if r.id == res.id:
                state = r.instances[0].state
                if state == 'running':
                    aws_id = r.instances[0].id
                    running_machines['simulation_state'] = aws_id
                    constellation.set_value('simulation_state',
                                            'network_setup')
                    done = True
                constellation.set_value("simulation_aws_state", state)
    constellation.set_value('simulation_launch_msg', "machine running")
    simulation_aws_id = running_machines['simulation_state']
    constellation.set_value('simulation_aws_id', simulation_aws_id)
    sim_tags = {'Name': sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([simulation_aws_id], sim_tags)

    # ec2conn.associate_address(router_aws_id, allocation_id=eip_allocation_id)
    sim_instance = get_ec2_instance(ec2conn, simulation_aws_id)
    sim_ip = sim_instance.ip_address
    clean_local_ssh_key_entry(sim_ip)
    constellation.set_value('simulation_ip', sim_ip)
    return sim_ip, simulation_aws_id, sim_key_pair_name


def terminate_aws_server(constellation_name):
    log("terminate AWS CloudSim [constellation %s]" % (constellation_name))
    constellation = ConstellationState(constellation_name)
    ec2conn = None
    try:
        running_machines = {}
        running_machines['simulation_aws_state'] = constellation.get_value(
                                                        'simulation_aws_id')
        ec2conn = aws_connect()[0]
        wait_for_multiple_machines_to_terminate(ec2conn, running_machines,
                                                constellation, max_retries=150)
        constellation.set_value('simulation_state', "terminated")
        constellation.set_value('simulation_launch_msg', "terminated")
        print ('Waiting after killing instances...')
        time.sleep(10.0)
    except Exception as e:
        log("error killing instances: %s" % e)
    try:
        sim_key_pair_name = constellation.get_value('sim_key_pair_name')
        ec2conn.delete_key_pair(sim_key_pair_name)
    except Exception as e:
        log("error cleaning up simulation key %s: %s" % (sim_key_pair_name, e))
    try:
        security_group_id = constellation.get_value('sim_security_group_id')
        ec2conn.delete_security_group(group_id=security_group_id)
    except Exception as e:
        log("error cleaning up security group %s: %s" % (security_group_id, e))


# def get_aws_sources_list(credentials_ec2):
#     """
#     Returns the package sources for the region
#     """
#     boto.config = BotoConfig(credentials_ec2)
#     # ec2conn = boto.connect_ec2()
#     availability_zone = boto.config.get('Boto', 'ec2_region_name')
# 
# #
# # Dublin 
# #
# deb http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise main restricted universe multiverse
# deb http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates main restricted universe multiverse
# deb http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise-security main restricted universe multiverse
# 
# deb-src http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise main restricted universe multiverse
# deb-src http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates main restricted universe multiverse
# deb-src http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/ precise-security main restricted universe multiverse
#
# East coast
# 
# deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise main restricted universe multiverse
# deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-updates main restricted universe multiverse
# deb http://us-east-1.ec2.archive.ubuntu.com/ubuntu/ precise-security main restricted universe multiverse


def acquire_aws_constellation(constellation_name,
                              credentials_ec2,
                              machines,
                              tags):
    """
    Creates a virtual network with machines inside. Each machine has
    - an elastic IP
    - a security group
    - a key (for the ubuntu user)
    """
    constellation = ConstellationState(constellation_name)

    constellation.set_value('machines', machines)

    ec2conn, vpcconn = aws_connect()
    availability_zone = boto.config.get('Boto', 'ec2_region_name')

    vpc_id, subnet_id = _acquire_vpc(constellation_name,
                                     vpcconn,
                                     availability_zone)
    log("VPC %s" % vpc_id)
    roles_to_reservations = {}
    for machine_name, machine_data in machines.iteritems():
        aws_key_name = _acquire_key_pair(constellation_name,
                          machine_name, ec2conn)

        security_group_id = _acquire_vpc_security_group(constellation_name,
                                    machine_name,
                                    VPN_PRIVATE_SUBNET,
                                    vpc_id,
                                    ec2conn)
        reservation_id = _acquire_vpc_server(constellation_name,
                                             machine_name,
                                             aws_key_name,
                                             machine_data,
                                             subnet_id,
                                             security_group_id,
                                             availability_zone,
                                             ec2conn)
        roles_to_reservations[machine_name] = reservation_id

    machines_to_awsid = wait_for_multiple_machines_to_run(ec2conn,
                                            roles_to_reservations,
                                            tags,
                                            constellation,
                                            max_retries=500,
                                            final_state='packages_setup')

    for machine_name, aws_id in machines_to_awsid.iteritems():
        m = "acquiring public Internet IP"
        constellation.set_value("%s_launch_msg" % machine_name, m)
        _acquire_vpc_elastic_ip(constellation_name,
                                machine_name,
                                aws_id,
                                ec2conn)
        if machine_name == "router":
            router_instance =  get_ec2_instance(ec2conn, aws_id)
            router_instance.modify_attribute('sourceDestCheck', False)

    log("running machines %s" % machines_to_awsid)


def terminate_aws_constellation(constellation_name, credentials_ec2):
    """
    Releases a private network, machines and all its resources
    """
    boto.config = BotoConfig(credentials_ec2)
    ec2conn, vpcconn = aws_connect()
    constellation = ConstellationState(constellation_name)

    machines = constellation.get_value('machines')
    log("machines: %s" % machines.keys())

    running_machines = {}
    for machine_prefix in machines.keys():
        try:
            state_key = '%s_aws_state' % machine_prefix
            aws_id_key = '%s_aws_id' % machine_prefix
            aws_id = constellation.get_value(aws_id_key)
            log("%s aws id: %s" % (machine_prefix, aws_id))
            running_machines[state_key] = aws_id
            m = "terminate machine instance"
            constellation.set_value("%s_launch_msg" % machine_prefix, m)
        except Exception, e:
            error_msg = constellation.get_value('error')
            error_msg += " get aws id error %s" % e
            constellation.set_value('error', error_msg)
    log("machines to terminate: %s" % running_machines)
    wait_for_multiple_machines_to_terminate(ec2conn,
                                            running_machines,
                                            constellation,
                                            max_retries=150)

    for machine_prefix in machines:
        m = "releasing ssh key"
        constellation.set_value("%s_launch_msg" % machine_prefix, m)
        _release_key_pair(constellation_name, machine_prefix, ec2conn)

    for machine_prefix in machines:
        m = "releasing security group"
        constellation.set_value("%s_launch_msg" % machine_prefix, m)
        released = False
        # this often fails... because machine does not appear dead to aws
        # so we retry
        count = 0
        while not released:
            time.sleep(count)
            if count > 0:
                log("_release_vpc_security_group retry")
            released = _release_vpc_security_group(constellation_name,
                                                   machine_prefix, ec2conn)
            count += 2
            if count > 10:
                released = True

    if "router" in machines:
        m = "releasing private network resources"
        constellation.set_value("%s_launch_msg" % "router", m)
    _release_vpc(constellation_name, vpcconn)

    for machine_prefix in machines:
        m = "releasing IP address"
        constellation.set_value("%s_launch_msg" % machine_prefix, m)
        _release_vpc_elastic_ip(constellation_name,
                                machine_prefix, ec2conn)


def __get_allocation_id_key(machine_name_prefix):
    allocation_id_key = '%s_eip_allocation_id' % machine_name_prefix
    return allocation_id_key


def _acquire_vpc_elastic_ip(constellation_name,
                            machine_name_prefix,
                            aws_id,
                            ec2conn):
    constellation = ConstellationState(constellation_name)
    try:
        aws_elastic_ip = ec2conn.allocate_address('vpc')
        allocation_id = aws_elastic_ip.allocation_id
        allocation_id_key = __get_allocation_id_key(machine_name_prefix)
        constellation.set_value(allocation_id_key, allocation_id)

        public_ip = aws_elastic_ip.public_ip
        log("%s elastic ip %s" % (machine_name_prefix,
                                  aws_elastic_ip.public_ip))
        ip_key = '%s_public_ip' % machine_name_prefix
        constellation.set_value(ip_key, public_ip)
        #
        # <Errors><Error><Code>InvalidAllocationID.NotFound</Code>
        #
        time.sleep(5)
        max = 20
        i = 0
        while i < max:
            try:
                time.sleep(i * 2)
                ec2conn.associate_address(aws_id, allocation_id=allocation_id)
                i = max  # leave the loop
            except:
                i += 1
                if i == max:
                    raise

        clean_local_ssh_key_entry(public_ip)
        return public_ip
    except Exception, e:
        constellation.set_value('error', "Elastic IP error: %s" % e)
        raise


def _release_vpc_elastic_ip(constellation_name, machine_name_prefix, ec2conn):
    constellation = ConstellationState(constellation_name)
    try:
        allocation_id_key = __get_allocation_id_key(machine_name_prefix)
        eip_allocation_id = constellation.get_value(allocation_id_key)
        ec2conn.release_address(allocation_id=eip_allocation_id)
    except Exception, e:
        error_msg = constellation.get_value('error')
        error_msg += "<b>Router IP address</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        print("error cleaning up %s elastic ip: %s" % (machine_name_prefix, e))


def _acquire_vpc(constellation_name, vpcconn, availability_zone):
    constellation = ConstellationState(constellation_name)
    vpc_id = None
    subnet_id = None
    try:
        constellation.set_value('router_launch_msg',
                                "creating virtual private network")
        aws_vpc = vpcconn.create_vpc(VPN_PRIVATE_SUBNET)
        vpc_id = aws_vpc.id
        constellation.set_value('vpc_id', vpc_id)

        aws_subnet = vpcconn.create_subnet(vpc_id, VPN_PRIVATE_SUBNET,
                                        availability_zone=availability_zone)
        subnet_id = aws_subnet.id
        constellation.set_value('subnet_id', subnet_id)

        constellation.set_value('router_launch_msg',
                                "setting up internet gateway")

        igw_id = vpcconn.create_internet_gateway().id
        constellation.set_value('igw_id', igw_id)
        vpcconn.attach_internet_gateway(igw_id, vpc_id)

        constellation.set_value('router_launch_msg', "creating routing tables")
        route_table_id = vpcconn.create_route_table(vpc_id).id
        constellation.set_value('route_table_id', route_table_id)

        vpcconn.create_route(route_table_id, '0.0.0.0/0', igw_id)
        route_table_association_id = vpcconn.associate_route_table(
                                                            route_table_id,
                                                            subnet_id)
        constellation.set_value('route_table_association_id',
                                route_table_association_id)

        i = 0
        while i < 5:
            # add a tag to the vpc so we can identify it
            try:
                log('adding tag to VPC %s' % i)
                aws_vpc.add_tag('constellation', constellation_name)
                i = 10
            except:
                i += 1
                time.sleep(i * 2)
    except Exception as e:
        constellation.set_value('error', "%s" % e)
        raise
    return vpc_id, subnet_id


def _release_vpc(constellation_name, vpcconn):
    constellation = ConstellationState(constellation_name)
    error_msg = constellation.get_value('error')
    original_error = error_msg

    vpc_id = None
    subnet_id = None
    igw_id = None
    route_table_association_id = None
    route_table_id = None
    try:
        vpc_id = constellation.get_value('vpc_id')
        subnet_id = constellation.get_value('subnet_id')
        igw_id = constellation.get_value('igw_id')
        route_table_id = constellation.get_value('route_table_id')
        route_table_association_id = constellation.get_value(
                                                'route_table_association_id')
    except Exception, e:
        error_msg += "%s" % e
        log("missing db key %s" % e)

    try:
        vpcconn.disassociate_route_table(route_table_association_id)
        vpcconn.delete_route(route_table_id, '0.0.0.0/0')
        vpcconn.delete_route_table(route_table_id)
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        log("error cleaning up routing table: %s" % e)

    try:
        vpcconn.detach_internet_gateway(igw_id, vpc_id)
        vpcconn.delete_internet_gateway(igw_id)
    except Exception, e:
        error_msg += "<b>Internet gateway</b>: %s<br>" % e
        log("error cleaning up internet gateway: %s" % e)

    try:
        vpcconn.delete_subnet(subnet_id)
    except Exception, e:
        error_msg += "<b>Subnet</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up subnet: %s" % e)

    try:
        vpcconn.delete_vpc(vpc_id)
    except Exception, e:
        error_msg += "<b>VPC</b>: %s<br>" % e
        log("error cleaning up vpc: %s" % e)

    if original_error != error_msg:
        constellation.set_value('error', error_msg)


def _get_security_group_key(machine_prefix):
    sg_key = '%s_security_group_id' % machine_prefix
    return sg_key


def _acquire_vpc_security_group(constellation_name,
                                machine_prefix,
                                vpn_subnet,
                                vpc_id,
                                ec2conn):
    constellation = ConstellationState(constellation_name)
    sg = None
    try:
        sg_name = '%s-sg-%s' % (machine_prefix, constellation_name)
        if machine_prefix == "router":
            dsc = 'router security group for %s' % (constellation_name)
            sg = ec2conn.create_security_group(sg_name, dsc, vpc_id)
            sg.authorize('udp', 1194, 1194, '0.0.0.0/0')   # openvpn
            sg.authorize('tcp', 22, 22, '0.0.0.0/0')   # ssh
            sg.authorize('icmp', -1, -1, '0.0.0.0/0')  # ping
            sg.authorize('udp', 0, 65535, vpn_subnet)
            sg.authorize('tcp', 0, 65535, vpn_subnet)
        else:
            dsc = '%s security group for %s vpc %s' % (machine_prefix,
                                                           constellation_name,
                                                           vpc_id)
            sg = ec2conn.create_security_group(sg_name, dsc, vpc_id)
            sg.authorize('icmp', -1, -1, vpn_subnet)
            sg.authorize('tcp',  0, 65535, vpn_subnet)
            sg.authorize('udp', 0, 65535, vpn_subnet)
            # Also allow all traffic from the OpenVPN client
            openvpn_client_addr = '%s/32' % (OPENVPN_CLIENT_IP)
            sg.authorize('icmp', -1, -1, openvpn_client_addr)
            sg.authorize('tcp', 0, 65535, openvpn_client_addr)
            sg.authorize('udp', 0, 65535, openvpn_client_addr)
        security_group_id = sg.id
        sg_key = _get_security_group_key(machine_prefix)
        constellation.set_value(sg_key, security_group_id)
    except Exception, e:
        constellation.set_value('error',  "security group error: %s" % e)
        raise

    i = 0
    while i < 5:
        log("adding tag to %s/%s security group" % (constellation_name,
                                                machine_prefix))
        try:
            sg.add_tag('vpc', vpc_id)
            sg.add_tag('constellation', constellation_name)
            i = 5
        except:
            time.sleep(i * 2)
    return security_group_id


def _release_vpc_security_group(constellation_name, machine_prefix, ec2conn):
    constellation = ConstellationState(constellation_name)
    security_group_id = None
    try:
        sg_key = _get_security_group_key(machine_prefix)
        security_group_id = constellation.get_value(sg_key)
        ec2conn.delete_security_group(group_id=security_group_id)
        return True
    except Exception, e:
        error_msg = constellation.get_value('error')
        error_msg += "<b>%s security group</b>: %s<br>" % (machine_prefix, e)
        constellation.set_value('error', error_msg)
        log("error cleaning up sim security group"
                            " %s: %s" % (security_group_id, e))
    return False


def _acquire_key_pair(constellation_name, machine_prefix, ec2conn):
    constellation = ConstellationState(constellation_name)
    try:
        constellation_directory = constellation.get_value(
                                                    'constellation_directory')
        key_pair_name = 'key-%s-%s' % (machine_prefix, constellation_name)
        key_pair = ec2conn.create_key_pair(key_pair_name)
        key_pair.save(constellation_directory)
        src = os.path.join(constellation_directory, '%s.pem' % key_pair_name)
        dst = os.path.join(constellation_directory,
                                    'key-%s.pem' % machine_prefix)
        shutil.copy(src, dst)
        return key_pair_name
    except Exception, e:
        constellation.set_value('error', "key error: %s" % e)
        raise


def _release_key_pair(constellation_name, machine_prefix, ec2conn):
    constellation = ConstellationState(constellation_name)
    key_pair_name = None
    try:
        key_pair_name = 'key-%s-%s' % (machine_prefix, constellation_name)
        ec2conn.delete_key_pair(key_pair_name)
    except Exception, e:
        error_msg = constellation.get_value('error')
        error_msg += "<b>Release key</b>: %s<br>" % e
        constellation.set_value('error', error_msg)
        log("error cleaning up simulation key %s: %s" % (key_pair_name, e))


def _acquire_vpc_server(constellation_name,
                        machine_prefix,
                        key_pair_name,
                        machine_data,
                        subnet_id,
                        security_group_id,
                        availability_zone,
                        ec2conn):
    amis = _get_amazon_amis(availability_zone)

    constellation = ConstellationState(constellation_name)
    try:
        constellation.set_value('%s_launch_msg' % machine_prefix, "booting")
        soft = machine_data['software']
        aws_image = amis[soft]
        aws_instance = machine_data['hardware']
        ip = machine_data['ip']
        startup_script = machine_data['startup_script']

        res = ec2conn.run_instances(aws_image,
                         instance_type=aws_instance,
                         subnet_id=subnet_id,
                         private_ip_address=ip,
                         security_group_ids=[security_group_id],
                         key_name=key_pair_name,
                         user_data=startup_script)
        return res.id
    except Exception, e:
        constellation.set_value('error', "%s" % e)
        raise


def aws_connect():
    config = get_cloudsim_config()
    credentials_ec2 = config['boto_path']
    boto.config = BotoConfig(credentials_ec2)

    ec2_zone = config['ec2_zone']

    aws_access_key_id = boto.config.get('Credentials', 'aws_access_key_id')
    aws_secret_access_key = boto.config.get('Credentials', 'aws_secret_access_key')

    if ec2_zone == 'nova':
        # TODO: remove hardcoded OpenStack endpoint
        region = RegionInfo(None, 'cloudsim', '172.16.0.201')
        ec2conn = EC2Connection(aws_access_key_id, aws_secret_access_key, is_secure=False,
            region=region, port=8773, path='/services/Cloud')

        vpcconn = VPCConnection(aws_access_key_id, aws_secret_access_key, is_secure=False,
            region=region, port=8773, path='/services/Cloud')
    else:
        ec2conn = boto.connect_ec2()
        vpcconn = boto.connect_vpc()
    return ec2conn, vpcconn


def _get_amazon_amis(availability_zone):
    """
    AMIs are the Amazon disk images. They have unique ids, and those ids vary
    in different regions
    """
#     config = get_cloudsim_config()
#     credentials_ec2 = config['boto_path']
#     boto.config = BotoConfig(credentials_ec2)
#     availability_zone = boto.config.get('Boto', 'ec2_region_name')

    amis = {}
    if availability_zone.startswith('eu-west'):
        amis['ubuntu_1204_x64_cluster'] = 'ami-fc191788'
        amis['ubuntu_1204_x64'] = 'ami-f2191786'

    elif availability_zone.startswith('us-east'):
        amis['ubuntu_1204_x64_cluster'] = 'ami-98fa58f1'
        amis['ubuntu_1204_x64'] = 'ami-137bcf7a'

    elif availability_zone.startswith('nova'):
        # TODO: we might want to move image ids to a configuration file
        ec2conn, _ = aws_connect()
        images = ec2conn.get_all_images(
            filters={'name': ['ubuntu-12.04.2-server-cloudimg-amd64-disk1']})
        for image in images:
            if image.name == 'ubuntu-12.04.2-server-cloudimg-amd64-disk1':
                amis['ubuntu_1204_x64_cluster'] = image.id
                amis['ubuntu_1204_x64'] = image.id

    return amis


def get_ec2_instance(ec2conn, mid):
    reservations = ec2conn.get_all_instances()
    instances = [i for r in reservations for i in r.instances]
    for i in instances:
        if i.id == mid:
            return i
    raise LaunchException("EC2 instance %s does not exist" % mid)


def wait_for_multiple_machines_to_run(ec2conn,
                                      names_to_reservations,
                                      tags,
                                      constellation,
                                      max_retries,
                                      initial_state="booting",
                                      final_state="network_setup"):
    """
    returns a dictionary of running machine ids indexed by role
    Writes xxx_state in redis, initially with initial state (booting)
    and final state when done (network_setup).
    It also writes tags for each aws instance (these tags can be read
    from the AWS EC2 console)

    """

    # mark all machines as "booting" (or other initial state)
    for machine_name in names_to_reservations.keys():
        constellation.set_value("%s_state" % machine_name, initial_state)

    reservations_to_roles = dict((v, k)
                                 for k, v in names_to_reservations.iteritems())

    ready_machines = {}
    count = max_retries + len(reservations_to_roles)

    while len(reservations_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            print("Waiting for running state: %s %s/%s " % (
                                                reservations_to_roles.values(),
                                                count,
                                                max_retries))
            if count < 0:
                msg = "timeout while waiting for EC2 machine(s)"
                msg += " %s" % reservations_to_roles
                raise LaunchException(msg)

            for r in ec2conn.get_all_instances():
                reservation = r.id
                if r.id in reservations_to_roles \
                        and r.instances[0].state == 'running':
                    machine_name = reservations_to_roles[reservation]
                    aws_id = r.instances[0].id
                    ready_machines[machine_name] = aws_id
                    reservations_to_roles.pop(reservation)

                    # add tags
                    machine_tags = {'Name': machine_name}
                    machine_tags.update(tags)
                    ec2conn.create_tags([aws_id], machine_tags)

                    # mark this machines state
                    constellation.set_value("%s_state" % machine_name,
                                            final_state)
                    constellation.set_value("%s_aws_id" % machine_name, aws_id)
                    log('Done launching %s (AWS %s)' % (machine_name, aws_id))
                    done = True
                    break
    return ready_machines


def wait_for_multiple_machines_to_terminate(ec2conn,
                                            roles_to_aws_ids,
                                            constellation,
                                            max_retries,
                                            final_state="terminated"):

    count = max_retries + len(roles_to_aws_ids)
    aws_ids_to_roles = dict((v, k) for k, v in roles_to_aws_ids.iteritems())

    missing_machines = {}
    for aws_id, role in aws_ids_to_roles.iteritems():
        log("terminate %s %s" % (role, aws_id))
        terminated = []
        try:
            terminated = ec2conn.terminate_instances(instance_ids=[aws_id])
        except Exception, e:
            log("FAILED to terminate  %s %s : %s" % (role, aws_id, e))
        if len(terminated) == 0:
            missing_machines[role] = aws_id
    if len(missing_machines) > 0:
        msg = "machine(s) %s not terminated" % missing_machines
        log(msg)

    # todo: recalc the aws_ids_to_roles without the missing machines
    while len(aws_ids_to_roles) > 0:
        done = False
        while not done:
            time.sleep(1)
            count = count - 1
            if count < 0:
                msg = "timeout while terminating EC2 machine(s) %s"
                msg = msg % aws_ids_to_roles
                raise LaunchException(msg)
            reservations = ec2conn.get_all_instances()
            instances = [i for r in reservations for i in r.instances]
            for instance in instances:
                aws_id = instance.id
                if aws_id in aws_ids_to_roles:
                    constellation.set_value(role, instance.state)
                    if instance.state == 'terminated':
                        role = aws_ids_to_roles[aws_id]
                        aws_ids_to_roles.pop(aws_id)
                        log('Terminated %s (AWS %s)' % (role, aws_id))
                        done = True
                        break
                    else:
                        log("%s (AWS %s) state: %s %s/%s" % (role,
                                    aws_id,
                                    instance.state,
                                    count,
                                    max_retries))
