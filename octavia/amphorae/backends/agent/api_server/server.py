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

import logging

import flask
import six
from werkzeug import exceptions

from octavia.amphorae.backends.agent import api_server
from octavia.amphorae.backends.agent.api_server import amphora_info
from octavia.amphorae.backends.agent.api_server import certificate_update
from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.backends.agent.api_server import plug


LOG = logging.getLogger(__name__)

app = flask.Flask(__name__)


# make the error pages all json
def make_json_error(ex):
    code = ex.code if isinstance(ex, exceptions.HTTPException) else 500
    response = flask.jsonify({'error': str(ex), 'http_code': code})
    response.status_code = code
    return response


for code in six.iterkeys(exceptions.default_exceptions):
    app.error_handler_spec[None][code] = make_json_error


# Tested with curl -k -XPUT --data-binary @/tmp/test.txt
# https://127.0.0.1:9443/0.5/listeners/123/haproxy
@app.route('/' + api_server.VERSION + '/listeners/<listener_id>/haproxy',
           methods=['PUT'])
def upload_haproxy_config(listener_id):
    return listener.upload_haproxy_config(listener_id)


@app.route('/' + api_server.VERSION + '/listeners/<listener_id>/haproxy',
           methods=['GET'])
def get_haproxy_config(listener_id):
    return listener.get_haproxy_config(listener_id)


@app.route('/' + api_server.VERSION +
           '/listeners/<listener_id>/<action>',
           methods=['PUT'])
def start_stop_listener(listener_id, action):
    return listener.start_stop_listener(listener_id, action)


@app.route('/' + api_server.VERSION +
           '/listeners/<listener_id>', methods=['DELETE'])
def delete_listener(listener_id):
    return listener.delete_listener(listener_id)


@app.route('/' + api_server.VERSION + '/details',
           methods=['GET'])
def get_details():
    return amphora_info.compile_amphora_details()


@app.route('/' + api_server.VERSION + '/info',
           methods=['GET'])
def get_info():
    return amphora_info.compile_amphora_info()


@app.route('/' + api_server.VERSION + '/listeners',
           methods=['GET'])
def get_all_listeners_status():
    return listener.get_all_listeners_status()


@app.route('/' + api_server.VERSION + '/listeners/<listener_id>',
           methods=['GET'])
def get_listener_status(listener_id):
    return listener.get_listener_status(listener_id)


@app.route('/' + api_server.VERSION + '/listeners/<listener_id>/certificates'
           + '/<filename>', methods=['PUT'])
def upload_certificate(listener_id, filename):
    return listener.upload_certificate(listener_id, filename)


@app.route('/' + api_server.VERSION + '/listeners/<listener_id>/certificates'
           + '/<filename>', methods=['GET'])
def get_certificate_md5(listener_id, filename):
    return listener.get_certificate_md5(listener_id, filename)


@app.route('/' + api_server.VERSION + '/listeners/<listener_id>/certificates'
           + '/<filename>', methods=['DELETE'])
def delete_certificate(listener_id, filename):
    return listener.delete_certificate(listener_id, filename)


@app.route('/' + api_server.VERSION + '/plug/vip/<vip>', methods=['POST'])
def plug_vip(vip):
    # Catch any issues with the subnet info json
    try:
        net_info = flask.request.get_json()
        assert type(net_info) is dict
        assert 'subnet_cidr' in net_info
        assert 'gateway' in net_info
        assert 'mac_address' in net_info
    except Exception:
        raise exceptions.BadRequest(description='Invalid subnet information')
    return plug.plug_vip(vip,
                         net_info['subnet_cidr'],
                         net_info['gateway'],
                         net_info['mac_address'])


@app.route('/' + api_server.VERSION + '/plug/network', methods=['POST'])
def plug_network():
    try:
        port_info = flask.request.get_json()
        assert type(port_info) is dict
        assert 'mac_address' in port_info
    except Exception:
        raise exceptions.BadRequest(description='Invalid port information')
    return plug.plug_network(port_info['mac_address'])


@app.route('/' + api_server.VERSION + '/certificate', methods=['PUT'])
def upload_cert():
    return certificate_update.upload_server_cert()
