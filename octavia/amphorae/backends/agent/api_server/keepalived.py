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

import os
import stat
import subprocess

import flask
import jinja2
from oslo_config import cfg
from oslo_log import log as logging
import webob

from octavia.amphorae.backends.agent.api_server import loadbalancer
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts


BUFFER = 100
CONF = cfg.CONF

LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
SYSTEMD_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSTEMD)
check_script_template = j2_env.get_template(consts.CHECK_SCRIPT_CONF)


class Keepalived:

    def upload_keepalived_config(self):
        stream = loadbalancer.Wrapped(flask.request.stream)

        if not os.path.exists(util.keepalived_dir()):
            os.makedirs(util.keepalived_dir())
        if not os.path.exists(util.keepalived_check_scripts_dir()):
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

        file_path = util.keepalived_init_path()

        template = SYSTEMD_TEMPLATE

        # Render and install the network namespace systemd service
        util.install_netns_systemd_service()
        util.run_systemctl_command(
            consts.ENABLE, consts.AMP_NETNS_SVC_PREFIX, False)

        # mode 00644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        if not os.path.exists(file_path):
            with os.fdopen(os.open(file_path, flags, mode), 'w') as text_file:
                text = template.render(
                    keepalived_pid=util.keepalived_pid_path(),
                    keepalived_cmd=consts.KEEPALIVED_CMD,
                    keepalived_cfg=util.keepalived_cfg_path(),
                    keepalived_log=util.keepalived_log_path(),
                    amphora_nsname=consts.AMPHORA_NAMESPACE,
                    amphora_netns=consts.AMP_NETNS_SVC_PREFIX,
                    administrative_log_facility=(
                        CONF.amphora_agent.administrative_log_facility),
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

        # Configure the monitoring of haproxy
        util.vrrp_check_script_update(None, consts.AMP_ACTION_START)

        # Make sure the new service is enabled on boot
        try:
            util.run_systemctl_command(consts.ENABLE,
                                       consts.KEEPALIVED_SYSTEMD)
        except subprocess.CalledProcessError as e:
            return webob.Response(json={
                'message': "Error enabling octavia-keepalived service",
                'details': e.output}, status=500)

        res = webob.Response(json={'message': 'OK'}, status=200)
        res.headers['ETag'] = stream.get_md5()

        return res

    def manager_keepalived_service(self, action):
        action = action.lower()
        if action not in [consts.AMP_ACTION_START,
                          consts.AMP_ACTION_STOP,
                          consts.AMP_ACTION_RELOAD]:
            return webob.Response(json={
                'message': 'Invalid Request',
                'details': f"Unknown action: {action}"}, status=400)

        if action == consts.AMP_ACTION_START:
            keepalived_pid_path = util.keepalived_pid_path()
            try:
                # Is there a pid file for keepalived?
                with open(keepalived_pid_path, encoding='utf-8') as pid_file:
                    pid = int(pid_file.readline())
                os.kill(pid, 0)

                # If we got here, it means the keepalived process is running.
                # We should reload it instead of trying to start it again.
                action = consts.AMP_ACTION_RELOAD
            except OSError:
                pass

        try:
            util.run_systemctl_command(action,
                                       consts.KEEPALIVED_SYSTEMD)
        except subprocess.CalledProcessError as e:
            return webob.Response(json={
                'message': f"Failed to {action} octavia-keepalived service",
                'details': e.output}, status=500)

        return webob.Response(
            json={'message': 'OK',
                  'details': f'keepalived {action}ed'},
            status=202)
