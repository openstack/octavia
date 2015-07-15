#    Copyright (c) 2015 Rackspace
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
import socket
import tempfile
import time

from oslo_log import log as logging
import paramiko
import six
from stevedore import driver as stevedore_driver

from octavia.amphorae.driver_exceptions import exceptions as exc
from octavia.amphorae.drivers import driver_base as driver_base
from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.common.config import cfg
from octavia.common import constants
from octavia.common.tls_utils import cert_parser
from octavia.i18n import _LW

LOG = logging.getLogger(__name__)
NEUTRON_VERSION = '2.0'
VIP_ROUTE_TABLE = 'vip'

# ip and route commands
CMD_DHCLIENT = "dhclient {0}"
CMD_ADD_IP_ADDR = "ip addr add {0}/24 dev {1}"
CMD_SHOW_IP_ADDR = "ip addr show {0}"
CMD_GREP_LINK_BY_MAC = ("ip link | grep {mac_address} -m 1 -B 1 "
                        "| awk 'NR==1{{print $2}}'")
CMD_CREATE_VIP_ROUTE_TABLE = (
    "su -c 'echo \"1 {0}\" >> /etc/iproute2/rt_tables'"
)
CMD_ADD_ROUTE_TO_TABLE = "ip route add {0} dev {1} table {2}"
CMD_ADD_DEFAULT_ROUTE_TO_TABLE = ("ip route add default via {0} "
                                  "dev {1} table {2}")
CMD_ADD_RULE_FROM_NET_TO_TABLE = "ip rule add from {0} table {1}"
CMD_ADD_RULE_TO_NET_TO_TABLE = "ip rule add to {0} table {1}"


class HaproxyManager(driver_base.AmphoraLoadBalancerDriver):

    amp_config = cfg.CONF.haproxy_amphora

    def __init__(self):
        super(HaproxyManager, self).__init__()
        self.amphoraconfig = {}
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=cfg.CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver
        self.jinja = jinja_cfg.JinjaTemplater(
            base_amp_path=self.amp_config.base_path,
            base_crt_dir=self.amp_config.base_cert_dir,
            haproxy_template=self.amp_config.haproxy_template)

    def get_logger(self):
        return LOG

    def update(self, listener, vip):
        LOG.debug("Amphora %s haproxy, updating listener %s, vip %s",
                  self.__class__.__name__, listener.protocol_port,
                  vip.ip_address)

        # Set a path variable to hold where configurations will live
        conf_path = '{0}/{1}'.format(self.amp_config.base_path, listener.id)

        # Process listener certificate info
        certs = self._process_tls_certificates(listener)

        # Generate HaProxy configuration from listener object
        config = self.jinja.build_config(listener, certs['tls_cert'])

        # Build a list of commands to send to the exec method
        commands = ['chmod 600 {0}/haproxy.cfg'.format(conf_path),
                    'haproxy -f {0}/haproxy.cfg -p {0}/{1}.pid -sf '
                    '$(cat {0}/{1}.pid)'.format(conf_path, listener.id)]

        # Exec appropriate commands on all amphorae
        self._exec_on_amphorae(
            listener.load_balancer.amphorae, commands,
            make_dir=conf_path, data=[config],
            upload_dir='{0}/haproxy.cfg'.format(conf_path))

    def stop(self, listener, vip):
        LOG.debug("Amphora %s haproxy, disabling listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)

        # Exec appropriate commands on all amphorae
        self._exec_on_amphorae(listener.load_balancer.amphorae,
                               ['kill -9 $(cat {0}/{1}/{1}.pid)'.format(
                                   self.amp_config.base_path, listener.id)])

    def delete(self, listener, vip):
        LOG.debug("Amphora %s haproxy, deleting listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)

        # Define the two operations that need to happen per amphora
        stop = 'kill -9 $(cat {0}/{1}/{1}.pid)'.format(
            self.amp_config.base_path, listener.id)
        delete = 'rm -rf {0}/{1}'.format(self.amp_config.base_path,
                                         listener.id)

        # Exec appropriate commands on all amphorae
        self._exec_on_amphorae(listener.load_balancer.amphorae, [stop, delete])

    def start(self, listener, vip):
        LOG.debug("Amphora %s haproxy, enabling listener %s, vip %s",
                  self.__class__.__name__,
                  listener.protocol_port, vip.ip_address)

        # Define commands to execute on the amphorae
        commands = [
            'haproxy -f {0}/{1}/haproxy.cfg -p {0}/{1}/{1}.pid'.format(
                self.amp_config.base_path, listener.id)]

        # Exec appropriate commands on all amphorae
        self._exec_on_amphorae(listener.load_balancer.amphorae, commands)

    def get_info(self, amphora):
        LOG.debug("Amphora %s haproxy, info amphora %s",
                  self.__class__.__name__, amphora.id)
        # info = self.amphora_client.get_info()
        # self.amphoraconfig[amphora.id] = (amphora.id, info)

    def get_diagnostics(self, amphora):
        LOG.debug("Amphora %s haproxy, get diagnostics amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'get_diagnostics')

    def finalize_amphora(self, amphora):
        LOG.debug("Amphora %s no-op, finalize amphora %s",
                  self.__class__.__name__, amphora.id)
        self.amphoraconfig[amphora.id] = (amphora.id, 'finalize amphora')

    def _configure_amp_routes(self, vip_iface, amp_net_config):
        subnet = amp_net_config.vip_subnet
        command = CMD_CREATE_VIP_ROUTE_TABLE.format(VIP_ROUTE_TABLE)
        self._execute_command(command, run_as_root=True)
        command = CMD_ADD_ROUTE_TO_TABLE.format(
            subnet.cidr, vip_iface, VIP_ROUTE_TABLE)
        self._execute_command(command, run_as_root=True)
        command = CMD_ADD_DEFAULT_ROUTE_TO_TABLE.format(
            subnet.gateway_ip, vip_iface, VIP_ROUTE_TABLE)
        self._execute_command(command, run_as_root=True)
        command = CMD_ADD_RULE_FROM_NET_TO_TABLE.format(
            subnet.cidr, VIP_ROUTE_TABLE)
        self._execute_command(command, run_as_root=True)
        command = CMD_ADD_RULE_TO_NET_TO_TABLE.format(
            subnet.cidr, VIP_ROUTE_TABLE)
        self._execute_command(command, run_as_root=True)

    def _configure_amp_interface(self, iface, secondary_ip=None):
        # just grab the ip from dhcp
        command = CMD_DHCLIENT.format(iface)
        self._execute_command(command, run_as_root=True)
        if secondary_ip:
            # add secondary_ip
            command = CMD_ADD_IP_ADDR.format(secondary_ip, iface)
            self._execute_command(command, run_as_root=True)
        # log interface details
        command = CMD_SHOW_IP_ADDR.format(iface)
        self._execute_command(command)

    def post_vip_plug(self, load_balancer, amphorae_network_config):
        LOG.debug("Add vip to interface for all amphora on %s",
                  load_balancer.id)

        for amp in load_balancer.amphorae:
            if amp.status != constants.DELETED:
                # Connect to amphora
                self._connect(hostname=amp.lb_network_ip)

                mac = amphorae_network_config.get(amp.id).vrrp_port.mac_address
                stdout, _ = self._execute_command(
                    CMD_GREP_LINK_BY_MAC.format(mac_address=mac))
                iface = stdout[:-2]
                if not iface:
                    self.client.close()
                    continue
                self._configure_amp_interface(
                    iface, secondary_ip=load_balancer.vip.ip_address)
                self._configure_amp_routes(
                    iface, amphorae_network_config.get(amp.id))

    def post_network_plug(self, amphora, port):
        self._connect(hostname=amphora.lb_network_ip)
        stdout, _ = self._execute_command(
            CMD_GREP_LINK_BY_MAC.format(mac_address=port.mac_address))
        iface = stdout[:-2]
        if not iface:
            self.client.close()
            return
        self._configure_amp_interface(iface)
        self.client.close()

    def _execute_command(self, command, run_as_root=False):
        if run_as_root and not self._is_root():
            command = "sudo {0}".format(command)
        _, stdout, stderr = self.client.exec_command(command)
        stdout = stdout.read()
        stderr = stderr.read()
        LOG.debug('Sent command {0}'.format(command))
        LOG.debug('Returned stdout: {0}'.format(stdout))
        LOG.debug('Returned stderr: {0}'.format(stderr))
        return stdout, stderr

    def _connect(self, hostname):
        for attempts in six.moves.xrange(
                self.amp_config.connection_max_retries):
            try:
                self.client.connect(hostname=hostname,
                                    username=self.amp_config.username,
                                    key_filename=self.amp_config.key_path)
            except socket.error:
                LOG.warn(_LW("Could not ssh to instance"))
                time.sleep(self.amp_config.connection_retry_interval)
                if attempts >= self.amp_config.connection_max_retries:
                    raise exc.TimeOutException()
            else:
                return
        raise exc.UnavailableException()

    def _process_tls_certificates(self, listener):
        """Processes TLS data from the listener.

        Converts and uploads PEM data to the Amphora API

        return TLS_CERT and SNI_CERTS
        """
        data = []

        certs = cert_parser.load_certificates_data(
            self.cert_manager, listener)
        sni_containers = certs['sni_certs']
        tls_cert = certs['tls_cert']
        if certs['tls_cert'] is not None:
            data.append(cert_parser.build_pem(tls_cert))
        if sni_containers:
            for sni_cont in sni_containers:
                data.append(cert_parser.build_pem(sni_cont))

        if data:
            cert_dir = os.path.join(self.amp_config.base_cert_dir, listener.id)
            listener_cert = '{0}/{1}.pem'.format(cert_dir, tls_cert.primary_cn)
            self._exec_on_amphorae(
                listener.load_balancer.amphorae, [
                    'chmod 600 {0}/*.pem'.format(cert_dir)],
                make_dir=cert_dir,
                data=data, upload_dir=listener_cert)

        return certs

    def _exec_on_amphorae(self, amphorae, commands, make_dir=None, data=None,
                          upload_dir=None):
        data = data or []
        temps = []
        # Write data to temp file to prepare for upload
        for datum in data:
            temp = tempfile.NamedTemporaryFile(delete=True)
            temp.write(datum.encode('ascii'))
            temp.flush()
            temps.append(temp)

        for amp in amphorae:
            if amp.status != constants.DELETED:
                # Connect to amphora
                self._connect(hostname=amp.lb_network_ip)

                # Setup for file upload
                if make_dir:
                    mkdir_cmd = 'mkdir -p {0}'.format(make_dir)
                    self._execute_command(mkdir_cmd, run_as_root=True)
                    chown_cmd = 'chown -R {0} {1}'.format(
                        self.amp_config.username, make_dir)
                    self._execute_command(chown_cmd, run_as_root=True)

                # Upload files to location
                if temps:
                    sftp = self.client.open_sftp()
                    for temp in temps:
                        sftp.put(temp.name, upload_dir)

                # Execute remaining commands
                for command in commands:
                    self._execute_command(command, run_as_root=True)
                self.client.close()

        # Close the temp file
        for temp in temps:
            temp.close()

    def _is_root(self):
        return cfg.CONF.haproxy_amphora.username == 'root'
