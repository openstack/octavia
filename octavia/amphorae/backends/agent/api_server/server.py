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
# under the License.

import os
import stat

import flask
from oslo_config import cfg
from oslo_log import log as logging
import six
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import amphora_info
from octavia.amphorae.backends.agent.api_server import certificate_update
from octavia.amphorae.backends.agent.api_server import keepalived
from octavia.amphorae.backends.agent.api_server import loadbalancer
from octavia.amphorae.backends.agent.api_server import osutils
from octavia.amphorae.backends.agent.api_server import plug
from octavia.amphorae.backends.agent.api_server import udp_listener_base
from octavia.amphorae.backends.agent.api_server import util

BUFFER = 1024
CONF = cfg.CONF
PATH_PREFIX = '/' + api_server.VERSION
LOG = logging.getLogger(__name__)


# make the error pages all json
def make_json_error(ex):
    code = ex.code if isinstance(ex, exceptions.HTTPException) else 500
    response = webob.Response(json={'error': str(ex), 'http_code': code})
    response.status_code = code
    return response


def register_app_error_handler(app):
    for code in six.iterkeys(exceptions.default_exceptions):
        app.register_error_handler(code, make_json_error)


class Server(object):
    def __init__(self):
        self.app = flask.Flask(__name__)
        self._osutils = osutils.BaseOS.get_os_util()
        self._keepalived = keepalived.Keepalived()
        self._loadbalancer = loadbalancer.Loadbalancer()
        self._udp_listener = (udp_listener_base.UdpListenerApiServerBase.
                              get_server_driver())
        self._plug = plug.Plug(self._osutils)
        self._amphora_info = amphora_info.AmphoraInfo(self._osutils)

        register_app_error_handler(self.app)

        self.app.add_url_rule(rule='/', view_func=self.version_discovery,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX +
                              '/loadbalancer/<amphora_id>/<lb_id>/haproxy',
                              view_func=self.upload_haproxy_config,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX +
                              '/listeners/<amphora_id>/<listener_id>'
                              '/udp_listener',
                              view_func=self.upload_udp_listener_config,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX +
                              '/loadbalancer/<lb_id>/haproxy',
                              view_func=self.get_haproxy_config,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX +
                              '/listeners/<listener_id>/udp_listener',
                              view_func=self.get_udp_listener_config,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX +
                              '/loadbalancer/<object_id>/<action>',
                              view_func=self.start_stop_lb_object,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/listeners/<object_id>',
                              view_func=self.delete_lb_object,
                              methods=['DELETE'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/config',
                              view_func=self.upload_config,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/details',
                              view_func=self.get_details,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/info',
                              view_func=self.get_info,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/listeners',
                              view_func=self.get_all_listeners_status,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/loadbalancer/<lb_id>'
                              '/certificates/<filename>',
                              view_func=self.upload_certificate,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/loadbalancer/<lb_id>'
                              '/certificates/<filename>',
                              view_func=self.get_certificate_md5,
                              methods=['GET'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/loadbalancer/<lb_id>'
                              '/certificates/<filename>',
                              view_func=self.delete_certificate,
                              methods=['DELETE'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/plug/vip/<vip>',
                              view_func=self.plug_vip,
                              methods=['POST'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/plug/network',
                              view_func=self.plug_network,
                              methods=['POST'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/certificate',
                              view_func=self.upload_cert, methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/vrrp/upload',
                              view_func=self.upload_vrrp_config,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/vrrp/<action>',
                              view_func=self.manage_service_vrrp,
                              methods=['PUT'])
        self.app.add_url_rule(rule=PATH_PREFIX + '/interface/<ip_addr>',
                              view_func=self.get_interface,
                              methods=['GET'])

    def upload_haproxy_config(self, amphora_id, lb_id):
        return self._loadbalancer.upload_haproxy_config(amphora_id, lb_id)

    def upload_udp_listener_config(self, amphora_id, listener_id):
        return self._udp_listener.upload_udp_listener_config(listener_id)

    def get_haproxy_config(self, lb_id):
        return self._loadbalancer.get_haproxy_config(lb_id)

    def get_udp_listener_config(self, listener_id):
        return self._udp_listener.get_udp_listener_config(listener_id)

    def start_stop_lb_object(self, object_id, action):
        protocol = util.get_protocol_for_lb_object(object_id)
        if protocol == 'UDP':
            return self._udp_listener.manage_udp_listener(
                listener_id=object_id, action=action)
        return self._loadbalancer.start_stop_lb(lb_id=object_id, action=action)

    def delete_lb_object(self, object_id):
        protocol = util.get_protocol_for_lb_object(object_id)
        if protocol == 'UDP':
            return self._udp_listener.delete_udp_listener(object_id)
        return self._loadbalancer.delete_lb(object_id)

    def get_details(self):
        return self._amphora_info.compile_amphora_details(
            extend_udp_driver=self._udp_listener)

    def get_info(self):
        return self._amphora_info.compile_amphora_info(
            extend_udp_driver=self._udp_listener)

    def get_all_listeners_status(self):
        udp_listeners = self._udp_listener.get_all_udp_listeners_status()
        return self._loadbalancer.get_all_listeners_status(
            other_listeners=udp_listeners)

    def upload_certificate(self, lb_id, filename):
        return self._loadbalancer.upload_certificate(lb_id, filename)

    def get_certificate_md5(self, lb_id, filename):
        return self._loadbalancer.get_certificate_md5(lb_id, filename)

    def delete_certificate(self, lb_id, filename):
        return self._loadbalancer.delete_certificate(lb_id, filename)

    def plug_vip(self, vip):
        # Catch any issues with the subnet info json
        try:
            net_info = flask.request.get_json()
            assert type(net_info) is dict
            assert 'subnet_cidr' in net_info
            assert 'gateway' in net_info
            assert 'mac_address' in net_info
        except Exception:
            raise exceptions.BadRequest(
                description='Invalid subnet information')
        return self._plug.plug_vip(vip,
                                   net_info['subnet_cidr'],
                                   net_info['gateway'],
                                   net_info['mac_address'],
                                   net_info.get('mtu'),
                                   net_info.get('vrrp_ip'),
                                   net_info.get('host_routes'))

    def plug_network(self):
        try:
            port_info = flask.request.get_json()
            assert type(port_info) is dict
            assert 'mac_address' in port_info
        except Exception:
            raise exceptions.BadRequest(description='Invalid port information')
        return self._plug.plug_network(port_info['mac_address'],
                                       port_info.get('fixed_ips'),
                                       port_info.get('mtu'))

    def upload_cert(self):
        return certificate_update.upload_server_cert()

    def upload_vrrp_config(self):
        return self._keepalived.upload_keepalived_config()

    def manage_service_vrrp(self, action):
        return self._keepalived.manager_keepalived_service(action)

    def get_interface(self, ip_addr):
        return self._amphora_info.get_interface(ip_addr)

    def upload_config(self):
        try:
            stream = flask.request.stream
            file_path = cfg.find_config_files(project=CONF.project,
                                              prog=CONF.prog)[0]
            flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
            # mode 00600
            mode = stat.S_IRUSR | stat.S_IWUSR
            with os.fdopen(os.open(file_path, flags, mode), 'wb') as cfg_file:
                b = stream.read(BUFFER)
                while b:
                    cfg_file.write(b)
                    b = stream.read(BUFFER)

            CONF.mutate_config_files()
        except Exception as e:
            LOG.error("Unable to update amphora-agent configuration: "
                      "{}".format(str(e)))
            return webob.Response(json=dict(
                message="Unable to update amphora-agent configuration.",
                details=str(e)), status=500)

        return webob.Response(json={'message': 'OK'}, status=202)

    def version_discovery(self):
        return webob.Response(json={'api_version': api_server.VERSION})
