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
import re
import stat
import subprocess

import jinja2
from oslo_config import cfg
from oslo_log import log as logging

from octavia.amphorae.backends.agent.api_server import osutils
from octavia.common import constants as consts

CONF = cfg.CONF
LOG = logging.getLogger(__name__)

FRONTEND_BACKEND_PATTERN = re.compile(r'\n(frontend|backend)\s+(\S+)\n')
LISTENER_MODE_PATTERN = re.compile(r'^\s+mode\s+(.*)$', re.MULTILINE)
TLS_CERT_PATTERN = re.compile(r'^\s+bind\s+\S+\s+ssl crt\s+(.*)$',
                              re.MULTILINE)
STATS_SOCKET_PATTERN = re.compile(r'stats socket\s+(\S+)')


class ParsingError(Exception):
    pass


class UnknownInitError(Exception):
    pass


def init_path(lb_id, init_system):
    if init_system == consts.INIT_SYSTEMD:
        return os.path.join(consts.SYSTEMD_DIR,
                            'haproxy-{0}.service'.format(lb_id))
    if init_system == consts.INIT_UPSTART:
        return os.path.join(consts.UPSTART_DIR,
                            'haproxy-{0}.conf'.format(lb_id))
    if init_system == consts.INIT_SYSVINIT:
        return os.path.join(consts.SYSVINIT_DIR,
                            'haproxy-{0}'.format(lb_id))
    raise UnknownInitError()


def keepalived_lvs_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'lvs')


def keepalived_lvs_init_path(init_system, listener_id):
    if init_system == consts.INIT_SYSTEMD:
        return os.path.join(consts.SYSTEMD_DIR,
                            consts.KEEPALIVED_SYSTEMD_PREFIX %
                            str(listener_id))
    elif init_system == consts.INIT_UPSTART:
        return os.path.join(consts.UPSTART_DIR,
                            consts.KEEPALIVED_UPSTART_PREFIX %
                            str(listener_id))
    elif init_system == consts.INIT_SYSVINIT:
        return os.path.join(consts.SYSVINIT_DIR,
                            consts.KEEPALIVED_SYSVINIT_PREFIX %
                            str(listener_id))
    else:
        raise UnknownInitError()


def keepalived_backend_check_script_dir():
    return os.path.join(CONF.haproxy_amphora.base_path, 'lvs/check/')


def keepalived_backend_check_script_path():
    return os.path.join(keepalived_backend_check_script_dir(),
                        'udp_check.sh')


def keepalived_lvs_pids_path(listener_id):
    pids_path = {}
    for file_ext in ['pid', 'vrrp.pid', 'check.pid']:
        pids_path[file_ext] = (
            os.path.join(CONF.haproxy_amphora.base_path,
                         ('lvs/octavia-keepalivedlvs-%s.%s') %
                         (str(listener_id), file_ext)))
    return pids_path['pid'], pids_path['vrrp.pid'], pids_path['check.pid']


def keepalived_lvs_cfg_path(listener_id):
    return os.path.join(CONF.haproxy_amphora.base_path,
                        ('lvs/octavia-keepalivedlvs-%s.conf') %
                        str(listener_id))


def haproxy_dir(lb_id):
    return os.path.join(CONF.haproxy_amphora.base_path, lb_id)


def pid_path(lb_id):
    return os.path.join(haproxy_dir(lb_id), lb_id + '.pid')


def config_path(lb_id):
    return os.path.join(haproxy_dir(lb_id), 'haproxy.cfg')


def get_haproxy_pid(lb_id):
    with open(pid_path(lb_id), 'r') as f:
        return f.readline().rstrip()


def get_keepalivedlvs_pid(listener_id):
    pid_file = keepalived_lvs_pids_path(listener_id)[0]
    with open(pid_file, 'r') as f:
        return f.readline().rstrip()


def haproxy_sock_path(lb_id):
    return os.path.join(CONF.haproxy_amphora.base_path, lb_id + '.sock')


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
    listeners = []
    for lb_id in get_loadbalancers():
        listeners_on_lb = parse_haproxy_file(lb_id)[1]
        listeners.extend(list(listeners_on_lb.keys()))
    return listeners


def get_loadbalancers():
    """Get Load balancers

    :returns: An array with the ids of all load balancers,
              e.g. ['123', '456', ...] or [] if no loadbalancers exist
    """
    if os.path.exists(CONF.haproxy_amphora.base_path):
        return [f for f in os.listdir(CONF.haproxy_amphora.base_path)
                if os.path.exists(config_path(f))]
    return []


def is_lb_running(lb_id):
    return os.path.exists(pid_path(lb_id)) and os.path.exists(
        os.path.join('/proc', get_haproxy_pid(lb_id)))


def get_udp_listeners():
    result = []
    if os.path.exists(keepalived_lvs_dir()):
        for f in os.listdir(keepalived_lvs_dir()):
            if f.endswith('.conf'):
                prefix = f.split('.')[0]
                if re.search("octavia-keepalivedlvs-", prefix):
                    result.append(f.split(
                        'octavia-keepalivedlvs-')[1].split('.')[0])
    return result


def is_udp_listener_running(listener_id):
    pid_file = keepalived_lvs_pids_path(listener_id)[0]
    return os.path.exists(pid_file) and os.path.exists(
        os.path.join('/proc', get_keepalivedlvs_pid(listener_id)))


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
                    if consts.INIT_UPSTART in str(init_version, 'utf-8'):
                        return consts.INIT_UPSTART
                    return consts.INIT_SYSVINIT
    return consts.INIT_UNKOWN


def install_netns_systemd_service():
    os_utils = osutils.BaseOS.get_os_util()

    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00644
    mode = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

    # TODO(bcafarel): implement this for other init systems
    # netns handling depends on a separate unit file
    netns_path = os.path.join(consts.SYSTEMD_DIR,
                              consts.AMP_NETNS_SVC_PREFIX + '.service')

    jinja_env = jinja2.Environment(
        autoescape=True, loader=jinja2.FileSystemLoader(os.path.dirname(
            os.path.realpath(__file__)
        ) + consts.AGENT_API_TEMPLATES))

    if not os.path.exists(netns_path):
        with os.fdopen(os.open(netns_path, flags, mode), 'w') as text_file:
            text = jinja_env.get_template(
                consts.AMP_NETNS_SVC_PREFIX + '.systemd.j2').render(
                    amphora_nsname=consts.AMPHORA_NAMESPACE,
                    HasIFUPAll=os_utils.has_ifup_all())
            text_file.write(text)


def run_systemctl_command(command, service):
    cmd = "systemctl {cmd} {srvc}".format(cmd=command, srvc=service)
    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.error("Failed to %(cmd)s %(srvc)s service: "
                  "%(err)s %(out)s", {'cmd': command, 'srvc': service,
                                      'err': e, 'out': e.output})


def get_protocol_for_lb_object(object_id):
    """Returns the L4 protocol for a listener.

    If the listener is a TCP based listener (haproxy) return TCP.
    If the listener is a UDP based listener (lvs) return UDP.
    If the listener is not identifiable, return None.

    :param listener_id: The ID of the listener to identify.
    :returns: TCP, UDP, or None
    """
    if os.path.exists(config_path(object_id)):
        return consts.PROTOCOL_TCP
    if os.path.exists(keepalived_lvs_cfg_path(object_id)):
        return consts.PROTOCOL_UDP
    return None


def parse_haproxy_file(lb_id):
    with open(config_path(lb_id), 'r') as file:
        cfg = file.read()

        listeners = {}

        m = FRONTEND_BACKEND_PATTERN.split(cfg)
        last_token = None
        last_id = None
        for section in m:
            if last_token is None:
                # We aren't in a section yet, see if this line starts one
                if section == 'frontend':
                    last_token = section
            elif last_token == 'frontend':
                # We're in a frontend section, save the id for later
                last_token = last_token + "_id"
                last_id = section
            elif last_token == 'frontend_id':
                # We're in a frontend section and already have the id
                # Look for the mode
                mode_matcher = LISTENER_MODE_PATTERN.search(section)
                if not mode_matcher:
                    raise ParsingError()
                listeners[last_id] = {
                    'mode': mode_matcher.group(1).upper(),
                }
                # Now see if this is a TLS frontend
                tls_matcher = TLS_CERT_PATTERN.search(section)
                if tls_matcher:
                    # TODO(rm_work): Can't we have terminated tcp?
                    listeners[last_id]['mode'] = 'TERMINATED_HTTPS'
                    listeners[last_id]['ssl_crt'] = tls_matcher.group(1)
                # Clear out the token and id and start over
                last_token = last_id = None

        m = STATS_SOCKET_PATTERN.search(cfg)
        if not m:
            raise ParsingError()
        stats_socket = m.group(1)

        return stats_socket, listeners
