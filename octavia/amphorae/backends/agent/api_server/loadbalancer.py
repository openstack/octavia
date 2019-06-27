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
import io
import os
import re
import shutil
import stat
import subprocess

import flask
import jinja2
from oslo_config import cfg
from oslo_log import log as logging
import six
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import haproxy_compatibility
from octavia.amphorae.backends.agent.api_server import osutils
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts
from octavia.common import utils as octavia_utils

LOG = logging.getLogger(__name__)
BUFFER = 100

CONF = cfg.CONF

UPSTART_CONF = 'upstart.conf.j2'
SYSVINIT_CONF = 'sysvinit.conf.j2'
SYSTEMD_CONF = 'systemd.conf.j2'

JINJA_ENV = jinja2.Environment(
    autoescape=True,
    loader=jinja2.FileSystemLoader(os.path.dirname(
        os.path.realpath(__file__)
    ) + consts.AGENT_API_TEMPLATES))
UPSTART_TEMPLATE = JINJA_ENV.get_template(UPSTART_CONF)
SYSVINIT_TEMPLATE = JINJA_ENV.get_template(SYSVINIT_CONF)
SYSTEMD_TEMPLATE = JINJA_ENV.get_template(SYSTEMD_CONF)


# Wrap a stream so we can compute the md5 while reading
class Wrapped(object):
    def __init__(self, stream_):
        self.stream = stream_
        self.hash = hashlib.md5()  # nosec

    def read(self, l):
        block = self.stream.read(l)
        if block:
            self.hash.update(block)
        return block

    def get_md5(self):
        return self.hash.hexdigest()

    def __getattr__(self, attr):
        return getattr(self.stream, attr)


class Loadbalancer(object):

    def __init__(self):
        self._osutils = osutils.BaseOS.get_os_util()

    def get_haproxy_config(self, lb_id):
        """Gets the haproxy config

        :param listener_id: the id of the listener
        """
        self._check_lb_exists(lb_id)
        with open(util.config_path(lb_id), 'r') as file:
            cfg = file.read()
            resp = webob.Response(cfg, content_type='text/plain')
            resp.headers['ETag'] = hashlib.md5(six.b(cfg)).hexdigest()  # nosec
            return resp

    def upload_haproxy_config(self, amphora_id, lb_id):
        """Upload the haproxy config

        :param amphora_id: The id of the amphora to update
        :param lb_id: The id of the loadbalancer
        """
        stream = Wrapped(flask.request.stream)
        # We have to hash here because HAProxy has a string length limitation
        # in the configuration file "peer <peername>" lines
        peer_name = octavia_utils.base64_sha1_string(amphora_id).rstrip('=')
        if not os.path.exists(util.haproxy_dir(lb_id)):
            os.makedirs(util.haproxy_dir(lb_id))

        name = os.path.join(util.haproxy_dir(lb_id), 'haproxy.cfg.new')
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        # mode 00600
        mode = stat.S_IRUSR | stat.S_IWUSR
        b = stream.read(BUFFER)
        s_io = io.StringIO()
        while b:
            # Write haproxy configuration to StringIO
            s_io.write(b.decode('utf8'))
            b = stream.read(BUFFER)

        # Since haproxy user_group is now auto-detected by the amphora agent,
        # remove it from haproxy configuration in case it was provided
        # by an older Octavia controller. This is needed in order to prevent
        # a duplicate entry for 'group' in haproxy configuration, which will
        # result an error when haproxy starts.
        new_config = re.sub(r"\s+group\s.+", "", s_io.getvalue())

        # Handle any haproxy version compatibility issues
        new_config = haproxy_compatibility.process_cfg_for_version_compat(
            new_config)

        with os.fdopen(os.open(name, flags, mode), 'w') as file:
            file.write(new_config)

        # use haproxy to check the config
        cmd = "haproxy -c -L {peer} -f {config_file} -f {haproxy_ug}".format(
            config_file=name, peer=peer_name,
            haproxy_ug=consts.HAPROXY_USER_GROUP_CFG)

        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.error("Failed to verify haproxy file: %s %s", e, e.output)
            # Save the last config that failed validation for debugging
            os.rename(name, ''.join([name, '-failed']))
            return webob.Response(
                json=dict(message="Invalid request", details=e.output),
                status=400)

        # file ok - move it
        os.rename(name, util.config_path(lb_id))

        try:

            init_system = util.get_os_init_system()

            LOG.debug('Found init system: %s', init_system)

            init_path = util.init_path(lb_id, init_system)

            if init_system == consts.INIT_SYSTEMD:
                template = SYSTEMD_TEMPLATE
                # Render and install the network namespace systemd service
                util.install_netns_systemd_service()
                util.run_systemctl_command(
                    consts.ENABLE, consts.AMP_NETNS_SVC_PREFIX + '.service')
            elif init_system == consts.INIT_UPSTART:
                template = UPSTART_TEMPLATE
            elif init_system == consts.INIT_SYSVINIT:
                template = SYSVINIT_TEMPLATE
                init_enable_cmd = "insserv {file}".format(file=init_path)
            else:
                raise util.UnknownInitError()

        except util.UnknownInitError:
            LOG.error("Unknown init system found.")
            return webob.Response(json=dict(
                message="Unknown init system in amphora",
                details="The amphora image is running an unknown init "
                        "system.  We can't create the init configuration "
                        "file for the load balancing process."), status=500)

        if init_system == consts.INIT_SYSTEMD:
            # mode 00644
            mode = (stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        else:
            # mode 00755
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)

        hap_major, hap_minor = haproxy_compatibility.get_haproxy_versions()
        if not os.path.exists(init_path):
            with os.fdopen(os.open(init_path, flags, mode), 'w') as text_file:

                text = template.render(
                    peer_name=peer_name,
                    haproxy_pid=util.pid_path(lb_id),
                    haproxy_cmd=util.CONF.haproxy_amphora.haproxy_cmd,
                    haproxy_cfg=util.config_path(lb_id),
                    haproxy_user_group_cfg=consts.HAPROXY_USER_GROUP_CFG,
                    respawn_count=util.CONF.haproxy_amphora.respawn_count,
                    respawn_interval=(util.CONF.haproxy_amphora.
                                      respawn_interval),
                    amphora_netns=consts.AMP_NETNS_SVC_PREFIX,
                    amphora_nsname=consts.AMPHORA_NAMESPACE,
                    HasIFUPAll=self._osutils.has_ifup_all(),
                    haproxy_major_version=hap_major,
                    haproxy_minor_version=hap_minor
                )
                text_file.write(text)

        # Make sure the new service is enabled on boot
        if init_system == consts.INIT_SYSTEMD:
            util.run_systemctl_command(
                consts.ENABLE, "haproxy-{lb_id}".format(lb_id=lb_id))
        elif init_system == consts.INIT_SYSVINIT:
            try:
                subprocess.check_output(init_enable_cmd.split(),
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to enable haproxy-%(lb_id)s service: "
                          "%(err)s %(out)s", {'lb_id': lb_id, 'err': e,
                                              'out': e.output})
                return webob.Response(json=dict(
                    message="Error enabling haproxy-{0} service".format(
                            lb_id), details=e.output), status=500)

        res = webob.Response(json={'message': 'OK'}, status=202)
        res.headers['ETag'] = stream.get_md5()

        return res

    def start_stop_lb(self, lb_id, action):
        action = action.lower()
        if action not in [consts.AMP_ACTION_START,
                          consts.AMP_ACTION_STOP,
                          consts.AMP_ACTION_RELOAD]:
            return webob.Response(json=dict(
                message='Invalid Request',
                details="Unknown action: {0}".format(action)), status=400)

        self._check_lb_exists(lb_id)

        # Since this script should be created at LB create time
        # we can check for this path to see if VRRP is enabled
        # on this amphora and not write the file if VRRP is not in use
        if os.path.exists(util.keepalived_check_script_path()):
            self.vrrp_check_script_update(lb_id, action)

        # HAProxy does not start the process when given a reload
        # so start it if haproxy is not already running
        if action == consts.AMP_ACTION_RELOAD:
            if consts.OFFLINE == self._check_haproxy_status(lb_id):
                action = consts.AMP_ACTION_START

        cmd = ("/usr/sbin/service haproxy-{lb_id} {action}".format(
            lb_id=lb_id, action=action))

        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            if b'Job is already running' not in e.output:
                LOG.debug(
                    "Failed to %(action)s haproxy-%(lb_id)s service: %(err)s "
                    "%(out)s", {'action': action, 'lb_id': lb_id,
                                'err': e, 'out': e.output})
                return webob.Response(json=dict(
                    message="Error {0}ing haproxy".format(action),
                    details=e.output), status=500)
        if action in [consts.AMP_ACTION_STOP,
                      consts.AMP_ACTION_RELOAD]:
            return webob.Response(json=dict(
                message='OK',
                details='Listener {lb_id} {action}ed'.format(
                    lb_id=lb_id, action=action)), status=202)

        details = (
            'Configuration file is valid\n'
            'haproxy daemon for {0} started'.format(lb_id)
        )

        return webob.Response(json=dict(message='OK', details=details),
                              status=202)

    def delete_lb(self, lb_id):
        try:
            self._check_lb_exists(lb_id)
        except exceptions.HTTPException:
            return webob.Response(json={'message': 'OK'})

        # check if that haproxy is still running and if stop it
        if os.path.exists(util.pid_path(lb_id)) and os.path.exists(
                os.path.join('/proc', util.get_haproxy_pid(lb_id))):
            cmd = "/usr/sbin/service haproxy-{0} stop".format(lb_id)
            try:
                subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to stop haproxy-%s service: %s %s",
                          lb_id, e, e.output)
                return webob.Response(json=dict(
                    message="Error stopping haproxy",
                    details=e.output), status=500)

        # parse config and delete stats socket
        try:
            stats_socket = util.parse_haproxy_file(lb_id)[0]
            os.remove(stats_socket)
        except Exception:
            pass

        # Since this script should be deleted at LB delete time
        # we can check for this path to see if VRRP is enabled
        # on this amphora and not write the file if VRRP is not in use
        if os.path.exists(util.keepalived_check_script_path()):
            self.vrrp_check_script_update(
                lb_id, action=consts.AMP_ACTION_STOP)

        # delete the ssl files
        try:
            shutil.rmtree(self._cert_dir(lb_id))
        except Exception:
            pass

        # disable the service
        init_system = util.get_os_init_system()
        init_path = util.init_path(lb_id, init_system)

        if init_system == consts.INIT_SYSTEMD:
            util.run_systemctl_command(
                consts.DISABLE, "haproxy-{lb_id}".format(
                    lb_id=lb_id))
        elif init_system == consts.INIT_SYSVINIT:
            init_disable_cmd = "insserv -r {file}".format(file=init_path)
        elif init_system != consts.INIT_UPSTART:
            raise util.UnknownInitError()

        if init_system == consts.INIT_SYSVINIT:
            try:
                subprocess.check_output(init_disable_cmd.split(),
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to disable haproxy-%(lb_id)s service: "
                          "%(err)s %(out)s", {'lb_id': lb_id, 'err': e,
                                              'out': e.output})
                return webob.Response(json=dict(
                    message="Error disabling haproxy-{0} service".format(
                            lb_id), details=e.output), status=500)

        # delete the directory + init script for that listener
        shutil.rmtree(util.haproxy_dir(lb_id))
        if os.path.exists(init_path):
            os.remove(init_path)

        return webob.Response(json={'message': 'OK'})

    def get_all_listeners_status(self, other_listeners=None):
        """Gets the status of all listeners

        This method will not consult the stats socket
        so a listener might show as ACTIVE but still be
        in ERROR

        Currently type==SSL is also not detected
        """
        listeners = list()

        for lb in util.get_loadbalancers():
            stats_socket, listeners_on_lb = util.parse_haproxy_file(lb)

            for listener_id, listener in listeners_on_lb.items():
                listeners.append({
                    'status': consts.ACTIVE,
                    'uuid': listener_id,
                    'type': listener['mode'],
                })

        if other_listeners:
            listeners = listeners + other_listeners
        return webob.Response(json=listeners, content_type='application/json')

    def upload_certificate(self, lb_id, filename):
        self._check_ssl_filename_format(filename)

        # create directory if not already there
        if not os.path.exists(self._cert_dir(lb_id)):
            os.makedirs(self._cert_dir(lb_id))

        stream = Wrapped(flask.request.stream)
        file = self._cert_file_path(lb_id, filename)
        flags = os.O_WRONLY | os.O_CREAT
        # mode 00600
        mode = stat.S_IRUSR | stat.S_IWUSR
        with os.fdopen(os.open(file, flags, mode), 'wb') as crt_file:
            b = stream.read(BUFFER)
            while b:
                crt_file.write(b)
                b = stream.read(BUFFER)

        resp = webob.Response(json=dict(message='OK'))
        resp.headers['ETag'] = stream.get_md5()
        return resp

    def get_certificate_md5(self, lb_id, filename):
        self._check_ssl_filename_format(filename)

        cert_path = self._cert_file_path(lb_id, filename)
        path_exists = os.path.exists(cert_path)
        if not path_exists:
            return webob.Response(json=dict(
                message='Certificate Not Found',
                details="No certificate with filename: {f}".format(
                    f=filename)), status=404)

        with open(cert_path, 'r') as crt_file:
            cert = crt_file.read()
            md5 = hashlib.md5(six.b(cert)).hexdigest()  # nosec
            resp = webob.Response(json=dict(md5sum=md5))
            resp.headers['ETag'] = md5
            return resp

    def delete_certificate(self, lb_id, filename):
        self._check_ssl_filename_format(filename)
        if os.path.exists(self._cert_file_path(lb_id, filename)):
            os.remove(self._cert_file_path(lb_id, filename))
        return webob.Response(json=dict(message='OK'))

    def _get_listeners_on_lb(self, lb_id):
        if os.path.exists(util.pid_path(lb_id)):
            if os.path.exists(
                    os.path.join('/proc', util.get_haproxy_pid(lb_id))):
                # Check if the listener is disabled
                with open(util.config_path(lb_id), 'r') as file:
                    cfg = file.read()
                    m = re.findall('^frontend (.*)$', cfg, re.MULTILINE)
                    return m or []
            else:  # pid file but no process...
                return []
        else:
            return []

    def _check_lb_exists(self, lb_id):
        # check if we know about that lb
        if lb_id not in util.get_loadbalancers():
            raise exceptions.HTTPException(
                response=webob.Response(json=dict(
                    message='Loadbalancer Not Found',
                    details="No loadbalancer with UUID: {0}".format(
                        lb_id)), status=404))

    def _check_ssl_filename_format(self, filename):
        # check if the format is (xxx.)*xxx.pem
        if not re.search('(\w.)+pem', filename):
            raise exceptions.HTTPException(
                response=webob.Response(json=dict(
                    message='Filename has wrong format'), status=400))

    def _cert_dir(self, lb_id):
        return os.path.join(util.CONF.haproxy_amphora.base_cert_dir, lb_id)

    def _cert_file_path(self, lb_id, filename):
        return os.path.join(self._cert_dir(lb_id), filename)

    def vrrp_check_script_update(self, lb_id, action):
        lb_ids = util.get_loadbalancers()
        if action == consts.AMP_ACTION_STOP:
            lb_ids.remove(lb_id)
        args = []
        for lbid in lb_ids:
            args.append(util.haproxy_sock_path(lbid))

        if not os.path.exists(util.keepalived_dir()):
            os.makedirs(util.keepalived_dir())
            os.makedirs(util.keepalived_check_scripts_dir())

        cmd = 'haproxy-vrrp-check {args}; exit $?'.format(args=' '.join(args))
        with open(util.haproxy_check_script_path(), 'w') as text_file:
            text_file.write(cmd)

    def _check_haproxy_status(self, lb_id):
        if os.path.exists(util.pid_path(lb_id)):
            if os.path.exists(
                    os.path.join('/proc', util.get_haproxy_pid(lb_id))):
                return consts.ACTIVE
        return consts.OFFLINE
