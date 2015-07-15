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

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess

import flask
import jinja2
import six
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.utils import haproxy_query as query
from octavia.common import constants as consts

LOG = logging.getLogger(__name__)
BUFFER = 100
HAPROXY_CONF = 'haproxy.conf.j2'

j2_env = jinja2.Environment(loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
template = j2_env.get_template(HAPROXY_CONF)


class ParsingError(Exception):
    pass


# Wrap a stream so we can compute the md5 while reading
class Wrapped(object):
    def __init__(self, stream_):
        self.stream = stream_
        self.hash = hashlib.md5()

    def read(self, l):
        block = self.stream.read(l)
        if block:
            self.hash.update(block)
        return block

    def get_md5(self):
        return self.hash.hexdigest()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


"""Gets the haproxy config

:param listenerid: the id of the listener
"""


def get_haproxy_config(listener_id):
    _check_listener_exists(listener_id)
    with open(util.config_path(listener_id), 'r') as file:
        cfg = file.read()
        resp = flask.Response(cfg, mimetype='text/plain', )
        resp.headers['ETag'] = hashlib.md5(six.b(cfg)).hexdigest()
        return resp


"""Upload the haproxy config

:param listener_id: The id of the listener
"""


def upload_haproxy_config(listener_id):
    stream = Wrapped(flask.request.stream)

    if not os.path.exists(util.haproxy_dir(listener_id)):
        os.makedirs(util.haproxy_dir(listener_id))

    name = os.path.join(util.haproxy_dir(listener_id), 'haproxy.cfg.new')
    with open(name, 'w') as file:
        b = stream.read(BUFFER)
        while (b):
            file.write(b)
            b = stream.read(BUFFER)

    # use haproxy to check the config
    cmd = "haproxy -c -f {config_file}".format(config_file=name)

    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.debug("Failed to verify haproxy file: {0}".format(e))
        os.remove(name)  # delete file
        return flask.make_response(flask.jsonify(dict(
            message="Invalid request",
            details=e.output)), 400)

    # file ok - move it
    os.rename(name, util.config_path(listener_id))

    if not os.path.exists(util.upstart_path(listener_id)):
        with open(util.upstart_path(listener_id), 'w') as text_file:
            text = template.render(
                haproxy_pid=util.pid_path(listener_id),
                haproxy_cmd=util.CONF.haproxy_amphora.haproxy_cmd,
                haproxy_cfg=util.config_path(listener_id),
                respawn_count=util.CONF.haproxy_amphora.respawn_count,
                respawn_interval=util.CONF.haproxy_amphora.respawn_interval
            )
            text_file.write(text)

    res = flask.make_response(flask.jsonify({
        'message': 'OK'}), 202)
    res.headers['ETag'] = stream.get_md5()
    return res


def start_stop_listener(listener_id, action):
    action = action.lower()
    if action not in ['start', 'stop', 'reload']:
        return flask.make_response(flask.jsonify(dict(
            message='Invalid Request',
            details="Unknown action: {0}".format(action))), 400)

    _check_listener_exists(listener_id)

    cmd = ("/usr/sbin/service haproxy-{listener_id} {action}".format(
        listener_id=listener_id, action=action))

    try:
        subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        LOG.debug("Failed to {0} HAProxy service: {1}".format(action, e))
        return flask.make_response(flask.jsonify(dict(
            message="Error {0}ing haproxy".format(action),
            details=e.output)), 500)
    if action in ['stop', 'reload']:
        return flask.make_response(flask.jsonify(
            dict(message='OK',
                 details='Listener {listener_id} {action}ed'.format(
                     listener_id=listener_id, action=action))), 202)

    details = (
        'Configuration file is valid\nhaproxy daemon for {0} '.format(
            listener_id) + 'started')

    return flask.make_response(flask.jsonify(
        dict(message='OK',
             details=details)), 202)


def delete_listener(listener_id):
    _check_listener_exists(listener_id)

    # check if that haproxy is still running and if stop it
    if os.path.exists(util.pid_path(listener_id)) and os.path.exists(
            os.path.join('/proc', util.get_haproxy_pid(listener_id))):
        cmd = "/usr/sbin/service haproxy-{0} stop".format(listener_id)
        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.debug("Failed to stop HAProxy service: {0}".format(e))
            return flask.make_response(flask.jsonify(dict(
                message="Error stopping haproxy",
                details=e.output)), 500)

    # parse config and delete stats socket
    try:
        cfg = _parse_haproxy_file(listener_id)
        os.remove(cfg['stats_socket'])
    except Exception:
        pass

    # delete the ssl files
    try:
        shutil.rmtree(_cert_dir(listener_id))
    except Exception:
        pass

    # delete the directory + upstart script for that listener
    shutil.rmtree(util.haproxy_dir(listener_id))
    if os.path.exists(util.upstart_path(listener_id)):
        os.remove(util.upstart_path(listener_id))

    return flask.jsonify({'message': 'OK'})


"""Gets the status of all listeners

This method will not consult the stats socket
so a listener might show as ACTIVE but still be
in ERROR

Currently type==SSL is also not detected
"""


def get_all_listeners_status():
    listeners = list()

    for listener in util.get_listeners():
        listeners.append({
            'status': _check_listener_status(listener),
            'uuid': listener,
            'type': _parse_haproxy_file(listener)['mode'],
        })

    # Can't use jsonify since lists are not supported
    # for security reason: http://stackoverflow.com/
    # questions/12435297/how-do-i-jsonify-a-list-in-flask
    return flask.Response(json.dumps(listeners),
                          mimetype='application/json')


"""Gets the status of a listener

This method will consult the stats socket
so calling this method will interfere with
the health daemon with the risk of the amphora
shut down

Currently type==SSL is not detected
"""


def get_listener_status(listener_id):
    _check_listener_exists(listener_id)

    status = _check_listener_status(listener_id)
    cfg = _parse_haproxy_file(listener_id)
    stats = dict(
        status=status,
        uuid=listener_id,
        type=cfg['mode']
    )
    # not active don't bother...
    if status != consts.ACTIVE:
        return flask.jsonify(stats)

    # read stats socket
    q = query.HAProxyQuery(cfg['stats_socket'])
    servers = q.get_pool_status()
    stats['pools'] = list(servers.values())
    return flask.jsonify(stats)


def upload_certificate(listener_id, filename):
    _check_listener_exists(listener_id)
    _check_ssl_filename_format(filename)

    # create directory if not already there
    if not os.path.exists(_cert_dir(listener_id)):
        os.makedirs(_cert_dir(listener_id))

    stream = Wrapped(flask.request.stream)
    with open(_cert_file_path(listener_id, filename), 'w') as crt_file:
        b = stream.read(BUFFER)
        while (b):
            crt_file.write(b)
            b = stream.read(BUFFER)
        os.fchmod(crt_file.fileno(), 0o600)  # only accessible by owner

    resp = flask.jsonify(dict(message='OK'))
    resp.headers['ETag'] = stream.get_md5()
    return resp


def get_certificate_md5(listener_id, filename):
    _check_listener_exists(listener_id)
    _check_ssl_filename_format(filename)

    cert_path = _cert_file_path(listener_id, filename)
    path_exists = os.path.exists(cert_path)
    if not path_exists:
        return flask.make_response(flask.jsonify(dict(
            message='Certificate Not Found',
            details="No certificate with filename: {f}".format(
                f=filename))), 404)

    with open(cert_path, 'r') as crt_file:
        cert = crt_file.read()
        md5 = hashlib.md5(six.b(cert)).hexdigest()
        resp = flask.jsonify(dict(md5sum=md5))
        resp.headers['ETag'] = md5
        return resp


def delete_certificate(listener_id, filename):
    _check_ssl_filename_format(filename)
    if not os.path.exists(_cert_file_path(listener_id, filename)):
        return flask.make_response(flask.jsonify(dict(
            message='Certificate Not Found',
            details="No certificate with filename: {f}".format(
                f=filename))), 404)

    os.remove(_cert_file_path(listener_id, filename))
    return flask.jsonify(dict(message='OK'))


def _check_listener_status(listener_id):
    if os.path.exists(util.pid_path(listener_id)):
        if os.path.exists(
                os.path.join('/proc', util.get_haproxy_pid(listener_id))):
            return consts.ACTIVE
        else:  # pid file but no process...
            return consts.ERROR
    else:
        return consts.OFFLINE


def _parse_haproxy_file(listener_id):
    with open(util.config_path(listener_id), 'r') as file:
        cfg = file.read()

        m = re.search('mode\s+(http|tcp)', cfg)
        if not m:
            raise ParsingError()
        mode = m.group(1).upper()

        m = re.search('stats socket\s+(\S+)', cfg)
        if not m:
            raise ParsingError()
        stats_socket = m.group(1)

        m = re.search('ssl crt\s+(\S+)', cfg)
        ssl_crt = None
        if m:
            ssl_crt = m.group(1)
            mode = 'TERMINATED_HTTPS'

        return dict(mode=mode,
                    stats_socket=stats_socket,
                    ssl_crt=ssl_crt)


def _check_listener_exists(listener_id):
    # check if we know about that listener
    if not os.path.exists(util.config_path(listener_id)):
        raise exceptions.HTTPException(
            response=flask.make_response(flask.jsonify(dict(
                message='Listener Not Found',
                details="No listener with UUID: {0}".format(
                    listener_id))), 404))


def _check_ssl_filename_format(filename):
    # check if the format is (xxx.)*xxx.pem
    if not re.search('(\w.)+pem', filename):
        raise exceptions.HTTPException(
            response=flask.make_response(flask.jsonify(dict(
                message='Filename has wrong format')), 400))


def _cert_dir(listener_id):
    return os.path.join(util.CONF.haproxy_amphora.base_cert_dir,
                        listener_id)


def _cert_file_path(listener_id, filename):
    return os.path.join(_cert_dir(listener_id), filename)