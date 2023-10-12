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
import queue
import stat
import time

from oslo_config import cfg
from oslo_log import log as logging
import simplejson

from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.health_daemon import health_sender
from octavia.amphorae.backends.utils import haproxy_query
from octavia.amphorae.backends.utils import keepalivedlvs_query


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
# ver 3 - Switch stats reporting to deltas

MSG_VER = 3

DELTA_METRICS = ('bin', 'bout', 'ereq', 'stot')

# Filesystem persistent counters for statistics deltas
COUNTERS = None
COUNTERS_FILE = None


def get_counters_file():
    global COUNTERS_FILE
    if COUNTERS_FILE is None:
        stats_file_path = os.path.join(
            CONF.haproxy_amphora.base_path, "stats_counters.json")
        # Open for read+write and create if necessary
        flags = os.O_RDWR | os.O_CREAT
        # mode 00644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
        try:
            COUNTERS_FILE = os.fdopen(
                os.open(stats_file_path, flags, mode), 'r+')
        except OSError:
            LOG.info("Failed to open `%s`, ignoring...", stats_file_path)
    COUNTERS_FILE.seek(0)
    return COUNTERS_FILE


def get_counters():
    global COUNTERS
    if COUNTERS is None:
        try:
            COUNTERS = simplejson.load(get_counters_file()) or {}
        except (simplejson.JSONDecodeError, AttributeError):
            COUNTERS = {}
    return COUNTERS


def persist_counters():
    """Attempt to persist the latest statistics values"""
    if COUNTERS is None:
        return
    try:
        stats = simplejson.dumps(COUNTERS)
        counters_file = get_counters_file()
        counters_file.truncate(0)
        counters_file.write(stats)
        counters_file.flush()
    except (OSError, AttributeError):
        LOG.warning("Couldn't persist statistics counter file!")


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
                with open(keepalived_pid_path,
                          'r', encoding='utf-8') as pid_file:
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
                LOG.exception('Failed to check keepalived and haproxy status '
                              'due to exception %s, skipping health '
                              'heartbeat.', str(e))
        except Exception as e:
            LOG.exception('Failed to check keepalived and haproxy status due '
                          'to exception %s, skipping health heartbeat.',
                          str(e))

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
    try:
        stats_query = haproxy_query.HAProxyQuery(stat_sock_file)
        stats = stats_query.show_stat()
        pool_status = stats_query.get_pool_status()
    except Exception as e:
        LOG.warning('Unable to query the HAProxy stats (%s) due to: %s',
                    stat_sock_file, str(e))
        # Return empty lists so that the heartbeat will still be sent
        return [], {}
    return stats, pool_status


def calculate_stats_deltas(listener_id, row):
    counters = get_counters()
    listener_counters = counters.get(listener_id, {})
    counters[listener_id] = listener_counters

    delta_values = {}
    for metric_key in DELTA_METRICS:
        current_value = int(row[metric_key])
        # Get existing counter for our metrics
        last_value = listener_counters.get(metric_key, 0)
        # Store the new absolute value
        listener_counters[metric_key] = current_value
        # Calculate a delta for each metric
        delta = current_value - last_value
        # Did HAProxy restart or reset counters?
        if delta < 0:
            delta = current_value  # If so, reset ours.
        delta_values[metric_key] = delta

    return delta_values


def build_stats_message():
    """Build a stats message based on retrieved listener statistics.

    Example version 3 message without UDP (note that values are deltas,
    not absolutes)::

        {"id": "<amphora_id>",
         "seq": 67,
         "listeners": {
           "<listener_id>": {
             "status": "OPEN",
             "stats": {
               "tx": 0,
               "rx": 0,
               "conns": 0,
               "totconns": 0,
               "ereq": 0
             }
           }
         },
         "pools": {
             "<pool_id>:<listener_id>": {
               "status": "UP",
               "members": {
                 "<member_id>": "no check"
               }
             }
         },
         "ver": 3
        }
    """
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
                    delta_values = calculate_stats_deltas(listener_id, row)
                    msg['listeners'][listener_id] = {
                        'status': row['status'],
                        'stats': {'tx': delta_values['bout'],
                                  'rx': delta_values['bin'],
                                  'conns': int(row['scur']),
                                  'totconns': delta_values['stot'],
                                  'ereq': delta_values['ereq']}}
            for pool_id, pool in pool_status.items():
                msg['pools'][pool_id] = {"status": pool['status'],
                                         "members": pool['members']}

    # UDP listener part
    lvs_listener_ids = util.get_lvs_listeners()
    if lvs_listener_ids:
        listeners_stats = keepalivedlvs_query.get_lvs_listeners_stats()
        if listeners_stats:
            for listener_id, listener_stats in listeners_stats.items():
                delta_values = calculate_stats_deltas(
                    listener_id, listener_stats['stats'])
                pool_status = (
                    keepalivedlvs_query.get_lvs_listener_pool_status(
                        listener_id))
                lvs_listener_dict = {}
                lvs_listener_dict['status'] = listener_stats['status']
                lvs_listener_dict['stats'] = {
                    'tx': delta_values['bout'],
                    'rx': delta_values['bin'],
                    'conns': listener_stats['stats']['scur'],
                    'totconns': delta_values['stot'],
                    'ereq': delta_values['ereq']
                }
                if pool_status:
                    pool_id = pool_status['lvs']['uuid']
                    msg['pools'][pool_id] = {
                        "status": pool_status['lvs']['status'],
                        "members": pool_status['lvs']['members']
                    }
                msg['listeners'][listener_id] = lvs_listener_dict
    persist_counters()
    return msg
