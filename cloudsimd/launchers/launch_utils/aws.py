from __future__ import print_function

import time
import shutil
import os

import boto.ec2
from boto.ec2.regioninfo import RegionInfo
from boto.ec2.connection import EC2Connection
from boto.vpc import VPCConnection
from boto.pyami.config import Config as BotoConfig

from launch_db import get_cloudsim_config
from launch_db import log_msg
from launch_db import ConstellationState
from sshclient import clean_local_ssh_key_entry
from launch_db import LaunchException


VPN_PRIVATE_SUBNET = '10.0.0.0/24'
OPENVPN_CLIENT_IP = '11.8.0.2'


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def get_aws_ubuntu_sources_repo(credentials_ec2):
    aws_connect(credentials_ec2)
    availability_zone = boto.config.get('Boto', 'ec2_region_name')
    if availability_zone.startswith('eu-west'):
        return "http://eu-west-1.ec2.archive.ubuntu.com/ubuntu/"
    elif availability_zone.startswith('us-east'):
        return "http://us-east-1.ec2.archive.ubuntu.com/ubuntu/"
    else:
        return "http://us.archive.ubuntu.com/ubuntu/"


def acquire_aws_single_server(constellation_name,
                       credentials_ec2,
                       constellation_directory,
                       machine_prefix,  # name of machine, ie "sim"
                       machine_data,
                       startup_script,
                       tags):
    sim_machine_name = "%s_%s" % (machine_prefix, constellation_name)

    ec2conn, _ = aws_connect(credentials_ec2)
    availability_zone = boto.config.get('Boto', 'ec2_region_name')
    amis = _get_amazon_amis(availability_zone)
    soft = machine_data['software']
    aws_image = amis[soft]
    aws_instance = machine_data['hardware']

    bdm = __get_block_device_mapping(aws_instance)

    constellation = ConstellationState(constellation_name)
    constellation.set_value('%s_launch_msg' % machine_prefix,
                            "setting up security groups")

    constellation_directory = constellation.get_value(
                                                    'constellation_directory')
    # save local startup script copy
    script_fname = os.path.join(constellation_directory,
                                    "%s_startup_script.txt" % machine_prefix)
    with open(script_fname, 'w') as f:
            f.write(startup_script)

    constellation.set_value('machine_name', machine_prefix)
    security_group_data = machine_data['security_group']
    security_group_name, security_group_id = _acquire_security_group(
                                    constellation_name,
                                    machine_prefix,
                                    security_group_data,
                                    vpc_id=None,
                                    ec2conn=ec2conn)

    key_pair_name = _acquire_key_pair(constellation_name,
                                      machine_prefix,
                                      ec2conn)

    roles_to_reservations = {}
    try:
        constellation.set_value('%s_launch_msg' % machine_prefix,
                                "requesting machine")
        res = ec2conn.run_instances(image_id=aws_image,
            instance_type=aws_instance,
            #subnet_id      = subnet_id,
            #private_ip_address=SIM_IP,
            security_groups=[security_group_name],
            key_name=key_pair_name,
            user_data=startup_script,
            block_device_map=bdm)
        roles_to_reservations['simulation_state'] = res.id
    except:
        log("ouch!")
        raise

    aws_id = None
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
                    constellation.set_value('%s_state' % machine_prefix,
                                            'network_setup')
                    done = True
                constellation.set_value('%s_aws_state' % machine_prefix, state)
    constellation.set_value('%s_launch_msg' % machine_prefix,
                            "machine running")
    constellation.set_value('%s_aws_id' % machine_prefix, aws_id)
    sim_tags = {'Name': sim_machine_name}
    sim_tags.update(tags)
    ec2conn.create_tags([aws_id], sim_tags)

    # ec2conn.associate_address(router_aws_id, allocation_id=eip_allocation_id)
    instance = get_ec2_instance(ec2conn, aws_id)
    ip = instance.ip_address
    clean_local_ssh_key_entry(ip)
    constellation.set_value('%s_public_ip' % (machine_prefix), ip)
    return ip, aws_id, key_pair_name


def terminate_aws_server(constellation_name, credentials_fname):
    log("terminate AWS CloudSim [constellation %s]" % (constellation_name))
    constellation = ConstellationState(constellation_name)
    ec2conn = None
    machine_prefix = constellation.get_value('machine_name')
    try:
        constellation.set_value('%s_state' % machine_prefix, "terminating")
        constellation.set_value('%s_launch_msg' % machine_prefix, "terminating")

        log("Terminate machine_prefix: %s" % machine_prefix)
        aws_id = constellation.get_value('%s_aws_id' % machine_prefix)
        log("Terminate aws_id: %s" % aws_id)
        running_machines = {machine_prefix: aws_id}
        ec2conn = aws_connect(credentials_fname)[0]
        wait_for_multiple_machines_to_terminate(ec2conn, running_machines,
                                                constellation, max_retries=150)
        constellation.set_value('%s_state' % machine_prefix, "terminated")
        print ('Waiting after killing instances...')
        time.sleep(10.0)
    except Exception as e:
        log("error killing instances: %s" % e)
    constellation.set_value('%s_launch_msg' % machine_prefix, "removing key")
    _release_key_pair(constellation_name, machine_prefix, ec2conn)
    constellation.set_value('%s_launch_msg' % machine_prefix,
                             "removing security group")
    _release_security_group(constellation_name, machine_prefix, ec2conn)
    constellation.set_value('%s_launch_msg' % machine_prefix, "terminated")


def acquire_aws_constellation(constellation_name,
                              credentials_ec2,
                              machines,
                              scripts,
                              tags):
    """
    Creates a virtual network with machines inside. Each machine has
    - an elastic IP
    - a security group
    - a key (for the ubuntu user)
    """
    constellation = ConstellationState(constellation_name)

    constellation.set_value('machines', machines)

    ec2conn, vpcconn = aws_connect(credentials_ec2)
    availability_zone = boto.config.get('Boto', 'ec2_region_name')

    vpc_id, subnet_id = _acquire_vpc(constellation_name,
                                     vpcconn,
                                     availability_zone)
    log("VPC %s" % vpc_id)
    roles_to_reservations = {}
    for machine_name, machine_data in machines.iteritems():
        aws_key_name = _acquire_key_pair(constellation_name,
                          machine_name, ec2conn)
        security_group_data = machines[machine_name]['security_group']
        _, security_group_id = _acquire_security_group(
                                    constellation_name,
                                    machine_name,
                                    security_group_data,
                                    vpc_id,
                                    ec2conn)
        startup_srcript = scripts[machine_name]
        reservation_id = _acquire_vpc_server(constellation_name,
                                             machine_name,
                                             aws_key_name,
                                             machine_data,
                                             startup_srcript,
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
            router_instance = get_ec2_instance(ec2conn, aws_id)
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
            aws_id_key = '%s_aws_id' % machine_prefix
            aws_id = constellation.get_value(aws_id_key)
            log("%s aws id: %s" % (machine_prefix, aws_id))
            running_machines[machine_prefix] = aws_id
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
                log("_release_security_group retry")
            released = _release_security_group(constellation_name,
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
        max_ = 20
        i = 0
        while i < max_:
            try:
                time.sleep(i * 2)
                ec2conn.associate_address(aws_id, allocation_id=allocation_id)
                i = max_  # leave the loop
            except:
                i += 1
                if i == max_:
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
        log("_release_vpc_elastic_ip %s machine %s id: %s" % (
                                    constellation_name,
                                    machine_name_prefix,
                                    eip_allocation_id))
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
        log("delete_vpc %s constellation %s" % (vpc_id, constellation_name))
        vpcconn.delete_vpc(vpc_id)
    except Exception, e:
        error_msg += "<b>VPC</b>: %s<br>" % e
        log("error cleaning up vpc: %s" % e)

    if original_error != error_msg:
        constellation.set_value('error', error_msg)


def _acquire_security_group(constellation_name,
                                machine_prefix,
                                security_group_data,
                                vpc_id,
                                ec2conn):
    constellation = ConstellationState(constellation_name)
    sg = None
    try:
        sg_name = '%s-sg-%s' % (machine_prefix, constellation_name)
        dsc = 'machine %s CloudSim constellation %s' % (machine_prefix,
                                            constellation_name,
                                            )
        sg = ec2conn.create_security_group(sg_name, dsc, vpc_id)

        max_try = 10
        i = 0
        while i < max_try:
            log("adding tag to %s/%s security group" % (constellation_name,
                                                machine_prefix))
            try:
                sg.add_tag('constellation', constellation_name)
                log("tag added")
                i = max_try
            except Exception, e:
                log("%s / %s: error: %s" % (i, max_try, e))
                i += 1
                time.sleep(i * 2)
                if i == max_try:
                    raise
        for rule in security_group_data:
            log("authorize %s" % (rule))
            sg.authorize(rule['protocol'],
                         rule['from_port'],
                         rule['to_port'],
                         rule['cidr'])

        security_group_id = sg.id
        security_group_name = sg.name

        constellation.set_value('%s_security_group_id' % machine_prefix,
                                security_group_id)
        constellation.set_value('%s_security_group_name' % machine_prefix,
                                security_group_name)
    except Exception, e:
        constellation.set_value('error',  "security group error: %s" % e)
        raise
    return security_group_name, security_group_id


def _release_security_group(constellation_name, machine_prefix, ec2conn):
    constellation = ConstellationState(constellation_name)
    security_group_id = None
    try:
        sg_key = '%s_security_group_id' % machine_prefix
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


def __get_block_device_mapping(aws_instance):
    """
    Resize the available disk space to 50 gig on certain instance types
    """
    bdm = None
    if aws_instance == 'cg1.4xlarge':
        dev_sda1 = boto.ec2.blockdevicemapping.EBSBlockDeviceType()
        dev_sda1.size = 50  # size in Gigabytes
        bdm = boto.ec2.blockdevicemapping.BlockDeviceMapping()
        bdm['/dev/sda1'] = dev_sda1
    #return bdm
    return None


def _acquire_vpc_server(constellation_name,
                        machine_prefix,
                        key_pair_name,
                        machine_data,
                        startup_script,
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
        bdm = __get_block_device_mapping(aws_instance)
        constellation_directory = constellation.get_value(
                                                    'constellation_directory')
        # save local startup script copy
        script_fname = os.path.join(constellation_directory,
                                    "%s_startup_script.txt" % machine_prefix)
        with open(script_fname, 'w') as f:
            f.write(startup_script)

        res = ec2conn.run_instances(aws_image,
                         instance_type=aws_instance,
                         subnet_id=subnet_id,
                         private_ip_address=ip,
                         security_group_ids=[security_group_id],
                         key_name=key_pair_name,
                         user_data=startup_script,
                         block_device_map=bdm)
        return res.id
    except:
        raise


def read_boto_file(credentials_ec2):
    boto.config = BotoConfig(credentials_ec2)
    ec2_region_name = boto.config.get('Boto', 'ec2_region_name')
    key_id = boto.config.get('Credentials', 'aws_access_key_id')
    aws_secret_access_key = boto.config.get('Credentials',
        'aws_secret_access_key')
    region_endpoint = boto.config.get('Boto', 'ec2_region_endpoint')
    return  ec2_region_name, key_id, aws_secret_access_key, region_endpoint


def aws_connect(creds_fname=None):
    credentials_ec2 = creds_fname
    if not credentials_ec2:
        config = get_cloudsim_config()
        # log("config: %s" % config)
        credentials_ec2 = config['boto_path']
    ec2_region_name, aws_access_key_id, aws_secret_access_key, region_endpoint\
        = read_boto_file(credentials_ec2)
    if ec2_region_name == 'nova':
        # TODO: remove hardcoded OpenStack endpoint
        region = RegionInfo(None, 'cloudsim', region_endpoint)  # 172.16.0.201
        ec2conn = EC2Connection(aws_access_key_id,
                                aws_secret_access_key,
                                is_secure=False,
                                region=region,
                                port=8773,
                                path='/services/Cloud')
        vpcconn = VPCConnection(aws_access_key_id,
                                aws_secret_access_key,
                                is_secure=False,
                                region=region,
                                port=8773,
                                path='/services/Cloud')
    else:
        region = RegionInfo(None, ec2_region_name, region_endpoint)
        ec2conn = boto.connect_ec2(aws_access_key_id,
                                   aws_secret_access_key,
                                   region=region)
        vpcconn = boto.connect_vpc(aws_access_key_id,
                                   aws_secret_access_key,
                                   region=region)
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
        # cloudsim 1.7.2
        amis['ubuntu_1204_x64_cloudsim_stable'] = 'ami-0f3ed378'
        amis['ubuntu_1204_x64_drc_router'] = 'ami-bcd235cb'
        amis['ubuntu_1204_x64_drc_simulator'] = 'ami-bad235cd'
        # simulator 1.7.2
        amis['ubuntu_1204_x64_simulator'] = 'ami-dd3fd2aa'

    elif availability_zone.startswith('us-east'):
        amis['ubuntu_1204_x64_cluster'] = 'ami-98fa58f1'
        amis['ubuntu_1204_x64'] = 'ami-137bcf7a'
        # cloudsim 1.7.2
        amis['ubuntu_1204_x64_cloudsim_stable'] = 'ami-f55f7b9c'
        amis['ubuntu_1204_x64_drc_router'] = 'ami-8d0155e4'
        amis['ubuntu_1204_x64_drc_simulator'] = 'ami-8f0155e6'
        # simulator 1.7.2
        amis['ubuntu_1204_x64_simulator'] = 'ami-8b5377e2'

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
                    constellation.set_value('%s_aws_state' % machine_name,
                                            'running')
                    log('Done launching machine %s'
                        '(AWS %s)' % (machine_name, aws_id))
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
                    state = instance.state
                    constellation.set_value("%s_aws_state" % role, state)
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
