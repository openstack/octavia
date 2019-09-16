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
from octavia.amphorae.backends.utils import keepalivedlvs_query


if six.PY2:
    import Queue as queue  # pylint: disable=wrong-import-order
else:
    import queue  # pylint: disable=wrong-import-order


CONF = cfg.CONF
LOG = logging.getLogger(__name__)
SEQ = 0
# MSG_VER is an incrementing integer heartbeat message format version
# this allows for backward compatibility when the amphora-agent is older
# than the controller version and the message format has backwards
# incompatible changes.
#
# ver 1 - Adds UDP listener status when no pool or members are present
# ver 2 - Switch to all listeners in a single combined haproxy config
#
MSG_VER = 2


def list_sock_stat_files(hadir=None):
    stat_sock_files = {}
    if hadir is None:
        hadir = CONF.haproxy_amphora.base_path
    lb_ids = util.get_loadbalancers()
    for lb_id in lb_ids:
        sock_file = lb_id + ".sock"
        stat_sock_files[lb_id] = os.path.join(hadir, sock_file)
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
        except (IOError, OSError) as e:
            if e.errno == errno.ENOENT:
                # Missing PID file, skip health heartbeat.
                LOG.error('Missing keepalived PID file %s, skipping health '
                          'heartbeat.', keepalived_pid_path)
            elif e.errno == errno.ESRCH:
                # Keepalived is not running, skip health heartbeat.
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
            if cmd == 'reload':
                LOG.info('Reloading configuration')
                CONF.reload_config_files()
            elif cmd == 'shutdown':
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
    # Example version 2 message without UDP:
    # {
    #   "id": "<amphora_id>",
    #   "seq": 67,
    #   "listeners": {
    #     "<listener_id>": {
    #       "status": "OPEN",
    #       "stats": {
    #         "tx": 0,
    #         "rx": 0,
    #         "conns": 0,
    #         "totconns": 0,
    #         "ereq": 0
    #       }
    #     }
    #  },
    #  "pools": {
    #    "<pool_id>:<listener_id>": {
    #      "status": "UP",
    #      "members": {
    #        "<member_id>": "no check"
    #      }
    #    }
    #  },
    #  "ver": 2
    # }
    global SEQ
    msg = {'id': CONF.amphora_agent.amphora_id,
           'seq': SEQ, 'listeners': {}, 'pools': {},
           'ver': MSG_VER}
    SEQ += 1
    stat_sock_files = list_sock_stat_files()
    # TODO(rm_work) There should only be one of these in the new config system
    for lb_id, stat_sock_file in stat_sock_files.items():
        if util.is_lb_running(lb_id):
            (stats, pool_status) = get_stats(stat_sock_file)
            for row in stats:
                if row['svname'] == 'FRONTEND':
                    listener_id = row['pxname']
                    msg['listeners'][listener_id] = {
                        'status': row['status'],
                        'stats': {'tx': int(row['bout']),
                                  'rx': int(row['bin']),
                                  'conns': int(row['scur']),
                                  'totconns': int(row['stot']),
                                  'ereq': int(row['ereq'])}}
            for pool_id, pool in pool_status.items():
                msg['pools'][pool_id] = {"status": pool['status'],
                                         "members": pool['members']}

    # UDP listener part
    udp_listener_ids = util.get_udp_listeners()
    if udp_listener_ids:
        listeners_stats = keepalivedlvs_query.get_udp_listeners_stats()
        if listeners_stats:
            for listener_id, listener_stats in listeners_stats.items():
                pool_status = keepalivedlvs_query.get_udp_listener_pool_status(
                    listener_id)
                udp_listener_dict = dict()
                udp_listener_dict['status'] = listener_stats['status']
                udp_listener_dict['stats'] = {
                    'tx': listener_stats['stats']['bout'],
                    'rx': listener_stats['stats']['bin'],
                    'conns': listener_stats['stats']['scur'],
                    'totconns': listener_stats['stats']['stot'],
                    'ereq': listener_stats['stats']['ereq']
                }
                if pool_status:
                    pool_id = pool_status['lvs']['uuid']
                    msg['pools'][pool_id] = {
                        "status": pool_status['lvs']['status'],
                        "members": pool_status['lvs']['members']
                    }
                msg['listeners'][listener_id] = udp_listener_dict
    return msg
