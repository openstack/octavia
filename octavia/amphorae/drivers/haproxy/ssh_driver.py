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
import socket
import tempfile
import time

from oslo_log import log as logging
import paramiko

from octavia.amphorae.driver_exceptions import exceptions as exc
from octavia.amphorae.drivers import driver_base as driver_base
from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.certificates.manager import barbican
from octavia.common.config import cfg
from octavia.common import data_models as data_models
from octavia.common.tls_utils import cert_parser
from octavia.i18n import _LW

LOG = logging.getLogger(__name__)


class HaproxyManager(driver_base.AmphoraLoadBalancerDriver):

    amp_config = cfg.CONF.haproxy_amphora

    def __init__(self):
        super(HaproxyManager, self).__init__()
        self.amphoraconfig = {}
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.barbican_client = barbican.BarbicanCertManager()
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
        config = self.jinja.build_config(listener, certs['tls_cert'],
                                         certs['sni_certs'])

        # Build a list of commands to send to the exec method
        commands = ['chmod 600 {0}/haproxy.cfg'.format(conf_path),
                    'sudo haproxy -f {0}/haproxy.cfg -p {0}/{1}.pid -sf '
                    '$(cat {0}/{1}.pid)'.format(conf_path, listener.id)]

        # Exec appropriate commands on all amphorae
        self._exec_on_amphorae(
            listener.load_balancer.amphorae, commands,
            make_dir='mkdir -p {0}'.format(conf_path), data=[config],
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
            'sudo haproxy -f {0}/{1}/haproxy.cfg -p {0}/{1}/{1}.pid'.format(
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

    def post_vip_plug(self, load_balancer):
        LOG.debug("Add vip to interface for all amphora on %s",
                  load_balancer.id)

        for amp in load_balancer.amphorae:
            # Connect to amphora
            self._connect(hostname=amp.lb_network_ip)

            _, stdout, _ = self.client.exec_command(
                "ip link | grep DOWN -m 1 | awk '{print $2}'")
            output = stdout.read()[:-2]
            vip = load_balancer.vip.ip_address
            sections = vip.split('.')[:3]
            sections.append('255')
            broadcast = '.'.join(sections)
            command = ("sudo sh -c 'echo \"\nauto {0} {0}:0\n"
                       "iface {0} inet dhcp\n\niface {0}:0 inet static\n"
                       "address {1}\nbroadcast {2}\nnetmask {3}\" "
                       ">> /etc/network/interfaces; ifup {0}; "
                       "ifup {0}:0'".format(output, vip, broadcast,
                                            '255.255.255.0'))
            self.client.exec_command(command)
            self.client.close()

    def post_network_plug(self, amphora):
        self._connect(hostname=amphora.lb_network_ip)
        _, stdout, _ = self.client.exec_command(
            "ip link | grep DOWN -m 1 | awk '{print $2}'")
        output = stdout.read()[:-2]
        command = ("sudo sh -c 'echo \"\nauto {0}\niface {0} inet dhcp\" "
                   ">> /etc/network/interfaces; ifup {0}'".format(output))
        self.client.exec_command(command)
        self.client.close()

    def _connect(self, hostname):
        for attempts in xrange(self.amp_config.connection_max_retries):
            try:
                self.client.connect(hostname=hostname,
                                    username=self.amp_config.username,
                                    key_filename=self.amp_config.key_name)
            except socket.error:
                LOG.warn(_LW("Could not ssh to instance"))
                time.sleep(self.amp_config.connection_retry_interval)
                if attempts >= self.amp_config.connection_max_retries:
                    raise exc.TimeOutException()
            else:
                return

    def _process_tls_certificates(self, listener):
        """Processes TLS data from the listener.

        Converts and uploads PEM data to the Amphora API

        return TLS_CERT and SNI_CERTS
        """
        tls_cert = None
        sni_certs = []
        cert_dir = '{0}/{1}/certificates'.format(self.amp_config.base_path,
                                                 listener.id)

        data = []

        if listener.tls_certificate_id:
            tls_cert = self._map_cert_tls_container(
                self.barbican_client.get_cert(listener.tls_certificate_id))
            data.append(self._build_pem(tls_cert))
        if listener.sni_containers:
            for sni_cont in listener.sni_containers:
                bbq_container = self._map_cert_tls_container(
                    self.barbican_client.get_cert(sni_cont.tls_container.id))
                sni_certs.append(bbq_container)
                data.append(self._build_pem(bbq_container))

        if data:
            self._exec_on_amphorae(listener.load_balancer.amphorae,
                                   ['chmod 600 {0}/*.pem'.format(cert_dir)],
                                   make_dir=cert_dir, data=data,
                                   upload_dir=cert_dir)

        return {'tls_cert': tls_cert, 'sni_certs': sni_certs}

    def _get_primary_cn(self, tls_cert):
        """Returns primary CN for Certificate."""
        return cert_parser.get_host_names(tls_cert.get_certificate())['cn']

    def _map_cert_tls_container(self, cert):
        return data_models.TLSContainer(
            primary_cn=self._get_primary_cn(cert),
            private_key=cert.get_private_key(),
            certificate=cert.get_certificate(),
            intermediates=cert.get_intermediates())

    def _build_pem(self, tls_cert):
        """Concatenate TLS Certificate fields to create a PEM

        encoded certificate file
        """
        # TODO(ptoohill): Maybe this should be part of utils or manager?
        pem = tls_cert.intermediates[:]
        pem.extend([tls_cert.certificate, tls_cert.private_key])

        return "\n".join(pem)

    def _exec_on_amphorae(self, amphorae, commands, make_dir=None, data=None,
                          upload_dir=None):
        data = data or []
        temps = []
        # Write data to temp file to prepare for upload
        for datum in data:
            temp = tempfile.NamedTemporaryFile(delete=True)
            temp.write(datum)
            temp.flush()
            temps.append(temp)

        for amp in amphorae:
            # Connect to amphora
            self._connect(hostname=amp.lb_network_ip)

            # Setup for file upload
            if make_dir:
                self.client.exec_command(make_dir)

            # Upload files to location
            if temps:
                sftp = self.client.open_sftp()
                for temp in temps:
                    sftp.put(temp.name, upload_dir)

            # Execute remaining commands
            for command in commands:
                self.client.exec_command(command)
            self.client.close()

        # Close the temp file
        for temp in temps:
            temp.close()
