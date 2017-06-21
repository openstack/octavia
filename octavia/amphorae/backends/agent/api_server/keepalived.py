# Copyright 2015 Hewlett Packard Enterprise Development Company LP
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
import os
import stat
import subprocess

import flask
import jinja2
import webob

from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts


BUFFER = 100

LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
UPSTART_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_UPSTART)
SYSVINIT_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSVINIT)
SYSTEMD_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSTEMD)
check_script_template = j2_env.get_template(consts.CHECK_SCRIPT_CONF)


class Keepalived(object):

    def upload_keepalived_config(self):
        stream = listener.Wrapped(flask.request.stream)

        if not os.path.exists(util.keepalived_dir()):
            os.makedirs(util.keepalived_dir())
            os.makedirs(util.keepalived_check_scripts_dir())

        conf_file = util.keepalived_cfg_path()
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        # mode 00644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        with os.fdopen(os.open(conf_file, flags, mode), 'wb') as f:
            b = stream.read(BUFFER)
            while b:
                f.write(b)
                b = stream.read(BUFFER)

        init_system = util.get_os_init_system()

        file_path = util.keepalived_init_path(init_system)

        if init_system == consts.INIT_SYSTEMD:
            template = SYSTEMD_TEMPLATE
            init_enable_cmd = "systemctl enable octavia-keepalived"
        elif init_system == consts.INIT_UPSTART:
            template = UPSTART_TEMPLATE
        elif init_system == consts.INIT_SYSVINIT:
            template = SYSVINIT_TEMPLATE
            init_enable_cmd = "insserv {file}".format(file=file_path)
        else:
            raise util.UnknownInitError()

        if init_system == consts.INIT_SYSTEMD:
            # mode 00644
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        else:
            # mode 00755
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
        if not os.path.exists(file_path):
            with os.fdopen(os.open(file_path, flags, mode), 'w') as text_file:
                text = template.render(
                    keepalived_pid=util.keepalived_pid_path(),
                    keepalived_cmd=consts.KEEPALIVED_CMD,
                    keepalived_cfg=util.keepalived_cfg_path(),
                    keepalived_log=util.keepalived_log_path(),
                    amphora_nsname=consts.AMPHORA_NAMESPACE
                )
                text_file.write(text)

            # Renders the Keepalived check script
            keepalived_path = util.keepalived_check_script_path()
            # mode 00755
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
            open_obj = os.open(keepalived_path, flags, mode)
            with os.fdopen(open_obj, 'w') as text_file:
                text = check_script_template.render(
                    check_scripts_dir=util.keepalived_check_scripts_dir()
                )
                text_file.write(text)

        # Make sure the new service is enabled on boot
        if init_system != consts.INIT_UPSTART:
            try:
                subprocess.check_output(init_enable_cmd.split(),
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.debug('Failed to enable octavia-keepalived service: '
                          '%(err)s', {'err': e})
                return webob.Response(json=dict(
                    message="Error enabling octavia-keepalived service",
                    details=e.output), status=500)

        res = webob.Response(json={'message': 'OK'}, status=200)
        res.headers['ETag'] = stream.get_md5()

        return res

    def manager_keepalived_service(self, action):
        action = action.lower()
        if action not in [consts.AMP_ACTION_START,
                          consts.AMP_ACTION_STOP,
                          consts.AMP_ACTION_RELOAD]:
            return webob.Response(json=dict(
                message='Invalid Request',
                details="Unknown action: {0}".format(action)), status=400)

        cmd = ("/usr/sbin/service octavia-keepalived {action}".format(
            action=action))

        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.debug('Failed to %s keepalived service: %s', action, e)
            return webob.Response(json=dict(
                message="Failed to {0} keepalived service".format(action),
                details=e.output), status=500)

        return webob.Response(
            json=dict(message='OK',
                      details='keepalived {action}ed'.format(action=action)),
            status=202)
