# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
#    under the License.


import os

from oslo_config import cfg

CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')
CONF.import_group('haproxy_amphora', 'octavia.common.config')
UPSTART_DIR = '/etc/init'


def upstart_path(listener_id):
    return os.path.join(UPSTART_DIR, ('haproxy-{0}.conf'.format(listener_id)))


def haproxy_dir(listener_id):
    return os.path.join(CONF.haproxy_amphora.base_path, listener_id)


def pid_path(listener_id):
    return os.path.join(haproxy_dir(listener_id), listener_id + '.pid')


def config_path(listener_id):
    return os.path.join(haproxy_dir(listener_id), 'haproxy.cfg')


def get_haproxy_pid(listener_id):
    with open(pid_path(listener_id), 'r') as f:
        return f.readline().rstrip()


"""Get Listeners

:returns An array with the ids of all listeners, e.g. ['123', '456', ...]
or [] if no listeners exist
"""


def get_listeners():
    if os.path.exists(CONF.haproxy_amphora.base_path):
        return [f for f in os.listdir(CONF.haproxy_amphora.base_path)
                if os.path.exists(config_path(f))]
    return []


def is_listener_running(listener_id):
    return os.path.exists(pid_path(listener_id)) and os.path.exists(
        os.path.join('/proc', get_haproxy_pid(listener_id)))


def get_network_interface_file(interface):
    return os.path.join(CONF.amphora_agent.agent_server_network_dir,
                        interface + '.cfg')
