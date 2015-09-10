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

import os
import time

from oslo_config import cfg
from oslo_log import log as logging
import six

from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.health_daemon import health_sender
from octavia.amphorae.backends.utils import haproxy_query
from octavia.i18n import _LI

if six.PY2:
    import Queue as queue
else:
    import queue

CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')
CONF.import_group('haproxy_amphora', 'octavia.common.config')
CONF.import_group('health_manager', 'octavia.common.config')
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
    LOG.info(_LI('Health Manager Sender starting.'))
    sender = health_sender.UDPStatusSender()
    while True:
        message = build_stats_message()
        sender.dosend(message)
        try:
            cmd = cmd_queue.get_nowait()
            if cmd is 'reload':
                LOG.info(_LI('Reloading configuration'))
                CONF.reload_config_files()
            elif cmd is 'shutdown':
                LOG.info(_LI('Health Manager Sender shutting down.'))
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
    for listener_id, stat_sock_file in six.iteritems(stat_sock_files):
        listener_dict = {'pools': {}, 'status': 'DOWN',
                                      'stats': {'tx': 0, 'rx': 0,
                                                'conns': 0, 'totconns': 0}}
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
                    listener_dict['status'] = row['status']
            for oid, pool in six.iteritems(pool_status):
                if oid != listener_id:
                    pool_id = oid
                    pools = listener_dict['pools']
                    pools[pool_id] = {"status": pool['status'],
                                      "members": pool['members']}
    return msg
