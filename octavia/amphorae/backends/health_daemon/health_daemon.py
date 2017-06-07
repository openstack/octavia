#! /usr/bin/env python

#    Copyright 2014 Hewlett-Packard Development Company, L.P.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import errno
import os
import time

from oslo_config import cfg
from oslo_log import log as logging
import six

from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.health_daemon import health_sender
from octavia.amphorae.backends.utils import haproxy_query

if six.PY2:
    import Queue as queue
else:
    import queue

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
SEQ = 0


def list_sock_stat_files(hadir=None):
    stat_sock_files = {}
    if hadir is None:
        hadir = CONF.haproxy_amphora.base_path
    listener_ids = util.get_listeners()
    for listener_id in listener_ids:
        sock_file = listener_id + ".sock"
        stat_sock_files[listener_id] = os.path.join(hadir, sock_file)
    return stat_sock_files


def run_sender(cmd_queue):
    LOG.info('Health Manager Sender starting.')
    sender = health_sender.UDPStatusSender()

    keepalived_cfg_path = util.keepalived_cfg_path()
    keepalived_pid_path = util.keepalived_pid_path()

    while True:

        try:
            # If the keepalived config file is present check
            # that it is running, otherwise don't send the health
            # heartbeat
            if os.path.isfile(keepalived_cfg_path):
                # Is there a pid file for keepalived?
                with open(keepalived_pid_path, 'r') as pid_file:
                    pid = int(pid_file.readline())
                os.kill(pid, 0)

            message = build_stats_message()
            sender.dosend(message)

        except IOError as e:
            # Missing PID file, skip health heartbeat
            if e.errno == errno.ENOENT:
                LOG.error('Missing keepalived PID file %s, skipping health '
                          'heartbeat.', keepalived_pid_path)
            else:
                LOG.error('Failed to check keepalived and haproxy status due '
                          'to exception %s, skipping health heartbeat.', e)
        except OSError as e:
            # Keepalived is not running, skip health heartbeat
            if e.errno == errno.ESRCH:
                LOG.error('Keepalived is configured but not running, '
                          'skipping health heartbeat.')
            else:
                LOG.error('Failed to check keepalived and haproxy status due '
                          'to exception %s, skipping health heartbeat.', e)
        except Exception as e:
            LOG.error('Failed to check keepalived and haproxy status due to '
                      'exception %s, skipping health heartbeat.', e)

        try:
            cmd = cmd_queue.get_nowait()
            if cmd is 'reload':
                LOG.info('Reloading configuration')
                CONF.reload_config_files()
            elif cmd is 'shutdown':
                LOG.info('Health Manager Sender shutting down.')
                break
        except queue.Empty:
            pass
        time.sleep(CONF.health_manager.heartbeat_interval)


def get_stats(stat_sock_file):
    stats_query = haproxy_query.HAProxyQuery(stat_sock_file)
    stats = stats_query.show_stat()
    pool_status = stats_query.get_pool_status()
    return stats, pool_status


def build_stats_message():
    global SEQ
    msg = {'id': CONF.amphora_agent.amphora_id,
           'seq': SEQ, "listeners": {}}
    SEQ += 1
    stat_sock_files = list_sock_stat_files()
    for listener_id, stat_sock_file in stat_sock_files.items():
        listener_dict = {'pools': {},
                         'status': 'DOWN',
                         'stats': {
                             'tx': 0,
                             'rx': 0,
                             'conns': 0,
                             'totconns': 0,
                             'ereq': 0}}
        msg['listeners'][listener_id] = listener_dict
        if util.is_listener_running(listener_id):
            (stats, pool_status) = get_stats(stat_sock_file)
            listener_dict = msg['listeners'][listener_id]
            for row in stats:
                if row['svname'] == 'FRONTEND':
                    listener_dict['stats']['tx'] = int(row['bout'])
                    listener_dict['stats']['rx'] = int(row['bin'])
                    listener_dict['stats']['conns'] = int(row['scur'])
                    listener_dict['stats']['totconns'] = int(row['stot'])
                    listener_dict['stats']['ereq'] = int(row['ereq'])
                    listener_dict['status'] = row['status']
            for oid, pool in pool_status.items():
                if oid != listener_id:
                    pool_id = oid
                    pools = listener_dict['pools']
                    pools[pool_id] = {"status": pool['status'],
                                      "members": pool['members']}
    return msg
