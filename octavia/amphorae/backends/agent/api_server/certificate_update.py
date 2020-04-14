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
import stat

import flask
from oslo_config import cfg
import webob

BUFFER = 1024

CONF = cfg.CONF


def upload_server_cert():
    stream = flask.request.stream
    file_path = CONF.amphora_agent.agent_server_cert
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    # mode 00600
    mode = stat.S_IRUSR | stat.S_IWUSR
    with os.fdopen(os.open(file_path, flags, mode), 'wb') as crt_file:
        b = stream.read(BUFFER)
        while b:
            crt_file.write(b)
            b = stream.read(BUFFER)

    return webob.Response(json={'message': 'OK'}, status=202)
