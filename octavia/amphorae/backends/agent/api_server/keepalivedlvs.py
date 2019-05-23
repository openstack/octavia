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
from oslo_log import log as logging
import webob
from werkzeug import exceptions

from octavia.amphorae.backends.agent.api_server import listener
from octavia.amphorae.backends.agent.api_server import udp_listener_base
from octavia.amphorae.backends.agent.api_server import util
from octavia.amphorae.backends.utils import keepalivedlvs_query
from octavia.common import constants as consts

BUFFER = 100
CHECK_SCRIPT_NAME = 'udp_check.sh'
KEEPALIVED_CHECK_SCRIPT_NAME = 'lvs_udp_check.sh'
LOG = logging.getLogger(__name__)

j2_env = jinja2.Environment(autoescape=True, loader=jinja2.FileSystemLoader(
    os.path.dirname(os.path.realpath(__file__)) + consts.AGENT_API_TEMPLATES))
UPSTART_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_UPSTART)
SYSVINIT_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSVINIT)
SYSTEMD_TEMPLATE = j2_env.get_template(consts.KEEPALIVED_JINJA2_SYSTEMD)
check_script_file_template = j2_env.get_template(
    consts.KEEPALIVED_CHECK_SCRIPT)


class KeepalivedLvs(udp_listener_base.UdpListenerApiServerBase):

    _SUBSCRIBED_AMP_COMPILE = ['keepalived', 'ipvsadm']

    def upload_udp_listener_config(self, listener_id):
        stream = listener.Wrapped(flask.request.stream)
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
            except Exception:
                raise exceptions.Conflict(
                    description='%(file_name)s not Found for '
                                'UDP Listener %(listener_id)s' %
                                {'file_name': CHECK_SCRIPT_NAME,
                                 'listener_id': listener_id})
            os.makedirs(util.keepalived_backend_check_script_dir())
            shutil.copy2(os.path.join(script_dir, CHECK_SCRIPT_NAME),
                         util.keepalived_backend_check_script_path())
            os.chmod(util.keepalived_backend_check_script_path(), stat.S_IEXEC)
        # Based on current topology setting, only the amphora instances in
        # Active-Standby topology will create the directory below. So for
        # Single topology, it should not create the directory and the check
        # scripts for status change.
        if not os.path.exists(util.keepalived_check_scripts_dir()):
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

        init_system = util.get_os_init_system()

        file_path = util.keepalived_lvs_init_path(init_system, listener_id)

        if init_system == consts.INIT_SYSTEMD:
            template = SYSTEMD_TEMPLATE

            # Render and install the network namespace systemd service
            util.install_netns_systemd_service()
            util.run_systemctl_command(
                consts.ENABLE, consts.AMP_NETNS_SVC_PREFIX)
        elif init_system == consts.INIT_UPSTART:
            template = UPSTART_TEMPLATE
        elif init_system == consts.INIT_SYSVINIT:
            template = SYSVINIT_TEMPLATE
        else:
            raise util.UnknownInitError()

        # Render and install the keepalivedlvs init script
        if init_system == consts.INIT_SYSTEMD:
            # mode 00644
            mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
        else:
            # mode 00755
            mode = (stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP |
                    stat.S_IROTH | stat.S_IXOTH)
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
                    amphora_netns=consts.AMP_NETNS_SVC_PREFIX
                )
                text_file.write(text)

        # Make sure the keepalivedlvs service is enabled on boot
        if init_system == consts.INIT_SYSTEMD:
            util.run_systemctl_command(
                consts.ENABLE, "octavia-keepalivedlvs-%s" % str(listener_id))
        elif init_system == consts.INIT_SYSVINIT:
            init_enable_cmd = "insserv {file}".format(file=file_path)
            try:
                subprocess.check_output(init_enable_cmd.split(),
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.debug('Failed to enable '
                          'octavia-keepalivedlvs service: '
                          '%(err)s', {'err': e})
                return webob.Response(json=dict(
                    message="Error enabling "
                            "octavia-keepalivedlvs service",
                    details=e.output), status=500)

        if NEED_CHECK:
            # inject the check script for keepalived process
            script_path = os.path.join(util.keepalived_check_scripts_dir(),
                                       KEEPALIVED_CHECK_SCRIPT_NAME)
            if not os.path.exists(script_path):
                with os.fdopen(os.open(script_path, flags, stat.S_IEXEC),
                               'w') as script_file:
                    text = check_script_file_template.render(
                        consts=consts,
                        init_system=init_system,
                        keepalived_lvs_pid_dir=util.keepalived_lvs_dir()
                    )
                    script_file.write(text)

        res = webob.Response(json={'message': 'OK'}, status=200)
        res.headers['ETag'] = stream.get_md5()
        return res

    def _check_udp_listener_exists(self, listener_id):
        if not os.path.exists(util.keepalived_lvs_cfg_path(listener_id)):
            raise exceptions.HTTPException(
                response=webob.Response(json=dict(
                    message='UDP Listener Not Found',
                    details="No UDP listener with UUID: {0}".format(
                        listener_id)), status=404))

    def get_udp_listener_config(self, listener_id):
        """Gets the keepalivedlvs config

        :param listener_id: the id of the listener
        """
        self._check_udp_listener_exists(listener_id)
        with open(util.keepalived_lvs_cfg_path(listener_id), 'r') as file:
            cfg = file.read()
            resp = webob.Response(cfg, content_type='text/plain')
            return resp

    def manage_udp_listener(self, listener_id, action):
        action = action.lower()
        if action not in [consts.AMP_ACTION_START,
                          consts.AMP_ACTION_STOP,
                          consts.AMP_ACTION_RELOAD]:
            return webob.Response(json=dict(
                message='Invalid Request',
                details="Unknown action: {0}".format(action)), status=400)

        # When octavia requests a reload of keepalived, force a restart since
        # a keepalived reload doesn't restore members in their initial state.
        #
        # TODO(gthiemonge) remove this when keepalived>=2.0.14 is widely use
        if action == consts.AMP_ACTION_RELOAD:
            action = consts.AMP_ACTION_RESTART

        self._check_udp_listener_exists(listener_id)
        if action == consts.AMP_ACTION_RELOAD:
            if consts.OFFLINE == self._check_udp_listener_status(listener_id):
                action = consts.AMP_ACTION_START

        cmd = ("/usr/sbin/service "
               "octavia-keepalivedlvs-{listener_id} "
               "{action}".format(listener_id=listener_id, action=action))

        try:
            subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            LOG.debug('Failed to %s keepalivedlvs listener %s',
                      listener_id + ' : ' + action, e)
            return webob.Response(json=dict(
                message=("Failed to {0} keepalivedlvs listener {1}"
                         .format(action, listener_id)),
                details=e.output), status=500)

        return webob.Response(
            json=dict(message='OK',
                      details='keepalivedlvs listener {listener_id}'
                              '{action}ed'.format(listener_id=listener_id,
                                                  action=action)),
            status=202)

    def _check_udp_listener_status(self, listener_id):
        if os.path.exists(util.keepalived_lvs_pids_path(listener_id)[0]):
            if os.path.exists(os.path.join(
                    '/proc', util.get_keepalivedlvs_pid(listener_id))):
                # Check if the listener is disabled
                with open(util.keepalived_lvs_cfg_path(listener_id),
                          'r') as file:
                    cfg = file.read()
                    m = re.search('virtual_server', cfg)
                    if m:
                        return consts.ACTIVE
                    return consts.OFFLINE
            return consts.ERROR
        return consts.OFFLINE

    def get_all_udp_listeners_status(self):
        """Gets the status of all UDP listeners

        Gets the status of all UDP listeners on the amphora.
        """
        listeners = list()

        for udp_listener in util.get_udp_listeners():
            status = self._check_udp_listener_status(udp_listener)
            listeners.append({
                'status': status,
                'uuid': udp_listener,
                'type': 'UDP',
            })
        return listeners

    def get_udp_listener_status(self, listener_id):
        """Gets the status of a UDP listener

        This method will consult the stats socket
        so calling this method will interfere with
        the health daemon with the risk of the amphora
        shut down

        :param listener_id: The id of the listener
        """
        self._check_udp_listener_exists(listener_id)

        status = self._check_udp_listener_status(listener_id)

        if status != consts.ACTIVE:
            stats = dict(
                status=status,
                uuid=listener_id,
                type='UDP'
            )
            return webob.Response(json=stats)

        stats = dict(
            status=status,
            uuid=listener_id,
            type='UDP'
        )

        try:
            pool = keepalivedlvs_query.get_udp_listener_pool_status(
                listener_id)
        except subprocess.CalledProcessError as e:
            return webob.Response(json=dict(
                message="Error getting kernel lvs status for udp listener "
                        "{}".format(listener_id),
                details=e.output), status=500)
        stats['pools'] = [pool]
        return webob.Response(json=stats)

    def delete_udp_listener(self, listener_id):
        try:
            self._check_udp_listener_exists(listener_id)
        except exceptions.HTTPException:
            return webob.Response(json={'message': 'OK'})

        # check if that keepalived is still running and if stop it
        keepalived_pid, vrrp_pid, check_pid = util.keepalived_lvs_pids_path(
            listener_id)
        if os.path.exists(keepalived_pid) and os.path.exists(
                os.path.join('/proc',
                             util.get_keepalivedlvs_pid(listener_id))):
            cmd = ("/usr/sbin/service "
                   "octavia-keepalivedlvs-{0} stop".format(listener_id))
            try:
                subprocess.check_output(cmd.split(), stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to stop keepalivedlvs service: %s", e)
                return webob.Response(json=dict(
                    message="Error stopping keepalivedlvs",
                    details=e.output), status=500)

        # Since the lvs check script based on the keepalived pid file for
        # checking whether it is alived. So here, we had stop the keepalived
        # process by the previous step, must make sure the pid files are not
        # exist.
        if (os.path.exists(keepalived_pid) or
                os.path.exists(vrrp_pid) or os.path.exists(check_pid)):
            for pid in [keepalived_pid, vrrp_pid, check_pid]:
                os.remove(pid)

        # disable the service
        init_system = util.get_os_init_system()
        init_path = util.keepalived_lvs_init_path(init_system, listener_id)

        if init_system == consts.INIT_SYSTEMD:
            util.run_systemctl_command(
                consts.DISABLE, "octavia-keepalivedlvs-%s" % str(listener_id))
        elif init_system == consts.INIT_SYSVINIT:
            init_disable_cmd = "insserv -r {file}".format(file=init_path)
        elif init_system != consts.INIT_UPSTART:
            raise util.UnknownInitError()

        if init_system == consts.INIT_SYSVINIT:
            try:
                subprocess.check_output(init_disable_cmd.split(),
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                LOG.error("Failed to disable "
                          "octavia-keepalivedlvs-%(list)s service: "
                          "%(err)s", {'list': listener_id, 'err': e})
                return webob.Response(json=dict(
                    message=(
                        "Error disabling octavia-keepalivedlvs-"
                        "{0} service".format(listener_id)),
                    details=e.output), status=500)

        # delete init script ,config file and log file for that listener
        if os.path.exists(init_path):
            os.remove(init_path)
        if os.path.exists(util.keepalived_lvs_cfg_path(listener_id)):
            os.remove(util.keepalived_lvs_cfg_path(listener_id))

        return webob.Response(json={'message': 'OK'})
