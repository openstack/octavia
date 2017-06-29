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
import subprocess

from oslo_config import cfg

from octavia.common import constants as consts

CONF = cfg.CONF


class UnknownInitError(Exception):
    pass


def init_path(listener_id, init_system):
    if init_system == consts.INIT_SYSTEMD:
        return os.path.join(consts.SYSTEMD_DIR,
                            'haproxy-{0}.service'.format(listener_id))
    elif init_system == consts.INIT_UPSTART:
        return os.path.join(consts.UPSTART_DIR,
                            'haproxy-{0}.conf'.format(listener_id))
    elif init_system == consts.INIT_SYSVINIT:
        return os.path.join(consts.SYSVINIT_DIR,
                            'haproxy-{0}'.format(listener_id))
    else:
        raise UnknownInitError()


def haproxy_dir(listener_id):
    return os.path.join(CONF.haproxy_amphora.base_path, listener_id)


def pid_path(listener_id):
    return os.path.join(haproxy_dir(listener_id), listener_id + '.pid')


def config_path(listener_id):
    return os.path.join(haproxy_dir(listener_id), 'haproxy.cfg')


def get_haproxy_pid(listener_id):
    with open(pid_path(listener_id), 'r') as f:
        return f.readline().rstrip()


def haproxy_sock_path(listener_id):
    return os.path.join(CONF.haproxy_amphora.base_path, listener_id + '.sock')


def haproxy_check_script_path():
    return os.path.join(keepalived_check_scripts_dir(),
                        'haproxy_check_script.sh')


def keepalived_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'vrrp')


def keepalived_init_path(init_system):
    if init_system == consts.INIT_SYSTEMD:
        return os.path.join(consts.SYSTEMD_DIR, consts.KEEPALIVED_SYSTEMD)
    elif init_system == consts.INIT_UPSTART:
        return os.path.join(consts.UPSTART_DIR, consts.KEEPALIVED_UPSTART)
    elif init_system == consts.INIT_SYSVINIT:
        return os.path.join(consts.SYSVINIT_DIR, consts.KEEPALIVED_SYSVINIT)
    else:
        raise UnknownInitError()


def keepalived_pid_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.pid')


def keepalived_cfg_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.conf')


def keepalived_log_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/octavia-keepalived.log')


def keepalived_check_scripts_dir():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/check_scripts')


def keepalived_check_script_path():
    return os.path.join(CONF.haproxy_amphora.base_path,
                        'vrrp/check_script.sh')


def get_listeners():
    """Get Listeners

    :returns: An array with the ids of all listeners, e.g. ['123', '456', ...]
              or [] if no listeners exist
    """

    if os.path.exists(CONF.haproxy_amphora.base_path):
        return [f for f in os.listdir(CONF.haproxy_amphora.base_path)
                if os.path.exists(config_path(f))]
    return []


def is_listener_running(listener_id):
    return os.path.exists(pid_path(listener_id)) and os.path.exists(
        os.path.join('/proc', get_haproxy_pid(listener_id)))


def get_os_init_system():
    if os.path.exists(consts.INIT_PROC_COMM_PATH):
        with open(consts.INIT_PROC_COMM_PATH, 'r') as init_comm:
            init_proc_name = init_comm.read().rstrip('\n')
            if init_proc_name == consts.INIT_SYSTEMD:
                return consts.INIT_SYSTEMD
            if init_proc_name == 'init':
                init_path = consts.INIT_PATH
                if os.path.exists(init_path):
                    args = [init_path, '--version']
                    init_version = subprocess.check_output(args, shell=False)
                    if consts.INIT_UPSTART in init_version:
                        return consts.INIT_UPSTART
                    else:
                        return consts.INIT_SYSVINIT
    return consts.INIT_UNKOWN
