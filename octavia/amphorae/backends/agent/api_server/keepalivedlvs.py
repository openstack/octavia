#    Copyright 2011-2014 OpenStack Foundation
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import re
import shutil
import stat
import subprocess

import flask
import jinja2
from oslo_config import cfg
from oslo_log import log as logging
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import loadbalancer
from octavia.amphorae.backends.agent.api_server import lvs_listener_base
from octavia.amphorae.backends.agent.api_server import util
from octavia.common import constants as consts

BUFFER = 100
CHECK_SCRIPT_NAME = 'udp_check.sh'
CONF = cfg.CONF
KEEPALIVED_CHECK_SCRIPT_NAME = 'lvs_udp_check.sh'
LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
SYSTEMD_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSTEMD)
check_script_file_template = j2_env.get_template(
    consts.KEEPALIVED_CHECK_SCRIPT)


class KeepalivedLvs(lvs_listener_base.LvsListenerApiServerBase):

    _SUBSCRIBED_AMP_COMPILE = ['keepalived', 'ipvsadm']

    def upload_lvs_listener_config(self, listener_id):
        stream = loadbalancer.Wrapped(flask.request.stream)
        NEED_CHECK = True

        if not os.path.exists(util.keepalived_lvs_dir()):
            os.makedirs(util.keepalived_lvs_dir())
        if not os.path.exists(util.keepalived_backend_check_script_dir()):
            current_file_dir, _ = os.path.split(os.path.abspath(__file__))

            try:
                script_dir = os.path.join(os.path.abspath(
                    os.path.join(current_file_dir, '../..')), 'utils')
                assert True is os.path.exists(script_dir)
                assert True is os.path.exists(os.path.join(
                    script_dir, CHECK_SCRIPT_NAME))
            except Exception as e:
                raise exceptions.Conflict(
                    description='%(file_name)s not Found for '
                                'UDP Listener %(listener_id)s' %
                                {'file_name': CHECK_SCRIPT_NAME,
                                 'listener_id': listener_id}) from e
            os.makedirs(util.keepalived_backend_check_script_dir())
            shutil.copy2(os.path.join(script_dir, CHECK_SCRIPT_NAME),
                         util.keepalived_backend_check_script_path())
            os.chmod(util.keepalived_backend_check_script_path(), stat.S_IEXEC)
        # Based on current topology setting, only the amphora instances in
        # Active-Standby topology will create the directory below. So for
        # Single topology, it should not create the directory and the check
        # scripts for status change.
        if (CONF.controller_worker.loadbalancer_topology !=
                consts.TOPOLOGY_ACTIVE_STANDBY):
            NEED_CHECK = False

        conf_file = util.keepalived_lvs_cfg_path(listener_id)
        flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
        # mode 00644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        with os.fdopen(os.open(conf_file, flags, mode), 'wb') as f:
            b = stream.read(BUFFER)
            while b:
                f.write(b)
                b = stream.read(BUFFER)

        file_path = util.keepalived_lvs_init_path(listener_id)

        template = SYSTEMD_TEMPLATE

        # Render and install the network namespace systemd service
        util.install_netns_systemd_service()
        util.run_systemctl_command(
            consts.ENABLE, consts.AMP_NETNS_SVC_PREFIX, False)

        # Render and install the keepalivedlvs init script
        # mode 00644
        mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        keepalived_pid, vrrp_pid, check_pid = util.keepalived_lvs_pids_path(
            listener_id)
        if not os.path.exists(file_path):
            with os.fdopen(os.open(file_path, flags, mode), 'w') as text_file:
                text = template.render(
                    keepalived_pid=keepalived_pid,
                    vrrp_pid=vrrp_pid,
                    check_pid=check_pid,
                    keepalived_cmd=consts.KEEPALIVED_CMD,
                    keepalived_cfg=util.keepalived_lvs_cfg_path(listener_id),
                    amphora_nsname=consts.AMPHORA_NAMESPACE,
                    amphora_netns=consts.AMP_NETNS_SVC_PREFIX,
                    administrative_log_facility=(
                        CONF.amphora_agent.administrative_log_facility),
                )
                text_file.write(text)

        # Make sure the keepalivedlvs service is enabled on boot
        try:
            util.run_systemctl_command(
                consts.ENABLE,
                consts.KEEPALIVEDLVS_SYSTEMD % listener_id)
        except subprocess.CalledProcessError as e:
            return webob.Response(json={
                'message': ("Error enabling "
                            "octavia-keepalivedlvs service"),
                'details': e.output}, status=500)

        if NEED_CHECK:
            # inject the check script for keepalived process
            script_path = os.path.join(util.keepalived_check_scripts_dir(),
                                       KEEPALIVED_CHECK_SCRIPT_NAME)
            if not os.path.exists(script_path):
                if not os.path.exists(util.keepalived_check_scripts_dir()):
                    os.makedirs(util.keepalived_check_scripts_dir())

                with os.fdopen(os.open(script_path, flags, stat.S_IEXEC),
                               'w') as script_file:
                    text = check_script_file_template.render(
                        consts=consts,
                        keepalived_lvs_pid_dir=util.keepalived_lvs_dir()
                    )
                    script_file.write(text)
            util.vrrp_check_script_update(None, consts.AMP_ACTION_START)

        res = webob.Response(json={'message': 'OK'}, status=200)
        res.headers['ETag'] = stream.get_md5()
        return res

    def _check_lvs_listener_exists(self, listener_id):
        if not os.path.exists(util.keepalived_lvs_cfg_path(listener_id)):
            raise exceptions.HTTPException(
                response=webob.Response(json={
                    'message': 'UDP Listener Not Found',
                    'details': f"No UDP listener with UUID: {listener_id}"},
                    status=404))

    def get_lvs_listener_config(self, listener_id):
        """Gets the keepalivedlvs config

        :param listener_id: the id of the listener
        """
        self._check_lvs_listener_exists(listener_id)
        with open(util.keepalived_lvs_cfg_path(listener_id),
                  encoding='utf-8') as file:
            cfg = file.read()
            resp = webob.Response(cfg, content_type='text/plain')
            return resp

    def manage_lvs_listener(self, listener_id, action):
        action = action.lower()
        if action not in [consts.AMP_ACTION_START,
                          consts.AMP_ACTION_STOP,
                          consts.AMP_ACTION_RELOAD]:
            return webob.Response(json={
                'message': 'Invalid Request',
                'details': f"Unknown action: {action}"}, status=400)

        # When octavia requests a reload of keepalived, force a restart since
        # a keepalived reload doesn't restore members in their initial state.
        #
        # TODO(gthiemonge) remove this when keepalived>=2.0.14 is widely use
        if action == consts.AMP_ACTION_RELOAD:
            action = consts.AMP_ACTION_RESTART

        self._check_lvs_listener_exists(listener_id)
        if action == consts.AMP_ACTION_RELOAD:
            if consts.OFFLINE == self._check_lvs_listener_status(listener_id):
                action = consts.AMP_ACTION_START

        try:
            util.run_systemctl_command(
                action, consts.KEEPALIVEDLVS_SYSTEMD % listener_id)
        except subprocess.CalledProcessError as e:
            return webob.Response(json={
                'message': (f"Failed to {action} keepalivedlvs listener "
                            f"{listener_id}"),
                'details': e.output}, status=500)

        return webob.Response(
            json={'message': 'OK',
                  'details': (f'keepalivedlvs listener {listener_id} '
                              f'{action}ed')},
            status=202)

    def _check_lvs_listener_status(self, listener_id):
        if os.path.exists(util.keepalived_lvs_pids_path(listener_id)[0]):
            if os.path.exists(os.path.join(
                    '/proc', util.get_keepalivedlvs_pid(listener_id))):
                # Check if the listener is disabled
                with open(util.keepalived_lvs_cfg_path(listener_id),
                          encoding='utf-8') as file:
                    cfg = file.read()
                    m = re.search('virtual_server', cfg)
                    if m:
                        return consts.ACTIVE
                    return consts.OFFLINE
            return consts.ERROR
        return consts.OFFLINE

    def get_all_lvs_listeners_status(self):
        """Gets the status of all UDP listeners

        Gets the status of all UDP listeners on the amphora.
        """
        listeners = []

        for lvs_listener in util.get_lvs_listeners():
            status = self._check_lvs_listener_status(lvs_listener)
            listeners.append({
                'status': status,
                'uuid': lvs_listener,
                'type': 'UDP',
            })
        return listeners

    def delete_lvs_listener(self, listener_id):
        try:
            self._check_lvs_listener_exists(listener_id)
        except exceptions.HTTPException:
            return webob.Response(json={'message': 'OK'})

        # check if that keepalived is still running and if stop it
        keepalived_pid, vrrp_pid, check_pid = util.keepalived_lvs_pids_path(
            listener_id)
        if os.path.exists(keepalived_pid) and os.path.exists(
                os.path.join('/proc',
                             util.get_keepalivedlvs_pid(listener_id))):
            try:
                util.run_systemctl_command(
                    consts.STOP,
                    consts.KEEPALIVEDLVS_SYSTEMD % listener_id)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to stop keepalivedlvs service: %s", e)
                return webob.Response(json={
                    'message': "Error stopping keepalivedlvs",
                    'details': e.output}, status=500)

        # Since the lvs check script based on the keepalived pid file for
        # checking whether it is alived. So here, we had stop the keepalived
        # process by the previous step, must make sure the pid files are not
        # exist.
        if (os.path.exists(keepalived_pid) or
                os.path.exists(vrrp_pid) or os.path.exists(check_pid)):
            for pid in [keepalived_pid, vrrp_pid, check_pid]:
                os.remove(pid)

        # disable the service
        init_path = util.keepalived_lvs_init_path(listener_id)

        try:
            util.run_systemctl_command(
                consts.DISABLE,
                consts.KEEPALIVEDLVS_SYSTEMD % listener_id)
        except subprocess.CalledProcessError as e:
            LOG.error("Failed to disable "
                      "octavia-keepalivedlvs-%(list)s service: "
                      "%(err)s", {'list': listener_id, 'err': str(e)})
            return webob.Response(json={
                'message': (
                    f"Error disabling octavia-keepalivedlvs-{listener_id} "
                    "service"),
                'details': e.output}, status=500)

        # delete init script ,config file and log file for that listener
        if os.path.exists(init_path):
            os.remove(init_path)
        if os.path.exists(util.keepalived_lvs_cfg_path(listener_id)):
            os.remove(util.keepalived_lvs_cfg_path(listener_id))

        return webob.Response(json={'message': 'OK'})
