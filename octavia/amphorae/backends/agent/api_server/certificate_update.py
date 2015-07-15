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

import flask
from oslo_config import cfg

MODE_OWNER = 0o600

BUFFER = 1024

CONF = cfg.CONF
CONF.import_group('amphora_agent', 'octavia.common.config')


def upload_server_cert():
    stream = flask.request.stream
    with open(CONF.amphora_agent.agent_server_cert, 'w') as crt_file:
        b = stream.read(BUFFER)
        while b:
            crt_file.write(b)
            b = stream.read(BUFFER)
        os.fchmod(crt_file.fileno(), MODE_OWNER)  # only accessible by owner

    return flask.make_response(flask.jsonify({
        'message': 'OK'}), 202)
