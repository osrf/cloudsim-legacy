from __future__ import print_function

from launch_utils.traffic_shaping import run_tc_command
from launch_utils.launch_db import log_msg, get_cloudsim_config,\
    ConstellationState, get_constellation_data
import json
import dateutil
import os
import subprocess
from launch_utils.sshclient import SshClient


def log(msg, channel=__name__, severity="info"):
    log_msg(msg, channel, severity)


def _start_simulator(ssh_client,
                    package_name,
                    launch_file_name,
                    launch_args,
                    task_timeout,
                    bash_src):

    c = "bash cloudsim/start_sim.bash %s %s %s %s" % (bash_src,
                                                      package_name,
                                                      launch_file_name,
                                                      launch_args)
    cmd = c.strip()
    r = ssh_client.cmd(cmd)
    log('_start_simulator %s' % r)


def start_ssh_task(ssh_client,
               constellation_name,
               machine_name_key,
               keyPairName,
               ip_address_key,
               task):

    latency = task['latency']
    up = task['uplink_data_cap']
    down = task['downlink_data_cap']
    run_tc_command(constellation_name,
                   machine_name_key,
                   keyPairName,
                   ip_address_key,
                   latency,
                   up,
                   down)

    log("** START SIMULATOR ***")
    try:
        _start_simulator(ssh_client,
                    task['ros_package'],
                    task['ros_launch'],
                    task['ros_args'],
                    task['timeout'],
                    task['bash_src'])
    finally:
        log("START TASK  DONE %s for %s" % (constellation_name, task))


def stop_ssh_task(ssh_client, constellation, task):

    log("** CONSTELLATION %s *** STOP TASK %s ***" % (constellation,
                                                      task['task_id']))
    _stop_simulator(constellation)

    log("** Notify portal ***")
    _notify_portal(constellation, task)


def _stop_simulator(ssh_client):
    cmd = "bash cloudsim/stop_sim.bash"
    r = ssh_client.cmd(cmd)
    log('_stop_simulator %s' % r)


def _notify_portal(constellation, task):
    try:
        root_log_dir = '/tmp/cloudsim_logs'

        # Get metadata (team, competition, ...)
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        log("** Portal JSON path: %s ***" % portal_info_fname)
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        log("** Portal JSON file opened ***")
        team = portal_info['team']
        comp = portal_info['event']
        task_num = task['vrc_num']

        log("** Team: %s, Event: %s ***" % (team, comp))

        if task_num < '1' or task_num > '3':
            task_num = '1'
        run = task['vrc_id']
        if run < '1' or run > '5':
            run = '1'

        start_time = task['start_time']
        start_task = dateutil.parser.parse(start_time)
        start_task = start_task.strftime("%d/%m/%y %H:%M:%S")

        const = ConstellationState(constellation)
        constellation_dict = get_constellation_data(constellation)
        constellation_directory = constellation_dict['constellation_directory']
        router_ip = const.get_value("router_public_ip")

        task_id = task['ros_launch']
        task_dirname = task_id.split('.')[0]

        # Store in this cloudsim the network and sim logs
        router_key = os.path.join(constellation_directory, 'key-router.pem')

        new_msg = task['task_message'] + '<B> Getting logs</B>'
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        cmd = ('bash /var/www/bin/get_logs.bash %s %s %s'
               % (task_dirname, router_ip, router_key))
        subprocess.check_call(cmd.split())
        log("** Log directory created***")

        # Get the score and falls
        score = '0'
        #falls = 'N/A'
        runtime = 'N/A'
        try:
            p = os.path.join(root_log_dir, task_dirname, 'score.log')
            with open(p) as f:
                log("** score.log found **")
                data = f.read()
                log("** Reading score.log file **")
                lines = data.split('\n')
                last_line = lines[-2]
                log("** Last line: %s **" % last_line)
                score = last_line.split(',')[4]
                #falls = last_line.split(',')[5]

                # Time when the task stopped
                runtime = last_line.split(',')[1]
                log("** All sim score fields parsed **")
        except Exception:
            None

        # Create JSON file with the task metadata
        data = json.dumps({'team': team, 'event': comp, 'task': task_num,
                           'start_time': start_task, 'result': 'Terminated',
                           'runtime': runtime, 'score': score},
                          sort_keys=True, indent=4, separators=(',', ': '))

        log("** JSON data created **")
        with open(os.path.join(root_log_dir, task_dirname,
                               'end_task.json'), 'w') as f:
            f.write(str(data))

        log("** JSON file created ***")

        new_msg = new_msg.replace('Getting logs', 'Creating tar file')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Tar all the log content
        tar_name = (team + '_' + comp + '_' + str(task_num) + '_' + str(run) +
                    '.tar')
        p = os.path.join(root_log_dir, task_dirname)
        cmd = 'tar cf /tmp/' + tar_name + ' -C ' + p + ' .'
        subprocess.check_call(cmd.split())

        log("** Log directory stored in a tar file ***")

        new_msg = new_msg.replace('Creating tar file',
                                  'Uploading logs to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

        # Send the log to the portal
        config = get_cloudsim_config()
        portal_info_fname = config['cloudsim_portal_json_path']
        portal_info = None
        with open(portal_info_fname, 'r') as f:
            portal_info = json.loads(f.read())

        ssh_portal = SshClient('xxx', 'xxx', portal_info['user'],
                               portal_info['hostname'])
        # this is a hack
        ssh_portal.key_fname = config['cloudsim_portal_key_path']

        # Upload the file to the Portal temp dir
        dest = os.path.join('/tmp', tar_name)

        cmd = ('scp -o UserKnownHostsFile=/dev/null'
               '-o StrictHostKeyChecking=no'
               ' -i ' + ssh_portal.key_fname + ' ' + dest + ' ubuntu@' +
               portal_info['hostname'] + ':/tmp')
        log('cmd: %s' % cmd)
        subprocess.check_call(cmd.split())

        # Move the file to the final destination into the Portal
        final_dest = os.path.join(portal_info['final_destination_dir'],
                                  tar_name)
        cmd = 'sudo mv %s %s' % (dest, final_dest)
        ssh_portal.cmd(cmd)

        new_msg = new_msg.replace('Uploading logs to the portal',
                                  'Logs uploaded to the portal')
        const.update_task_value(task['task_id'], 'task_message', new_msg)

    except Exception, excep:
        log('notify_portal() Exception: %s' % (repr(excep)))
        raise
