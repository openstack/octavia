# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2015 Rackspace
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

import functools
import hashlib
import time

from oslo_log import log as logging
import requests
import six
from stevedore import driver as stevedore_driver

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.amphorae.drivers import driver_base as driver_base
from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.amphorae.drivers.haproxy.jinja import jinja_cfg
from octavia.common.config import cfg
from octavia.common import constants
from octavia.common import data_models as data_models
from octavia.common.tls_utils import cert_parser
from octavia.i18n import _LW

LOG = logging.getLogger(__name__)
API_VERSION = '0.5'
OCTAVIA_API_CLIENT = (
    "Octavia HaProxy Rest Client/{version} "
    "(https://wiki.openstack.org/wiki/Octavia)").format(version=API_VERSION)
CONF = cfg.CONF
CONF.import_group('haproxy_amphora', 'octavia.common.config')


class HaproxyAmphoraLoadBalancerDriver(driver_base.AmphoraLoadBalancerDriver):
    def __init__(self):
        super(HaproxyAmphoraLoadBalancerDriver, self).__init__()
        self.client = AmphoraAPIClient()
        self.cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver
        self.jinja = jinja_cfg.JinjaTemplater(
            base_amp_path=CONF.haproxy_amphora.base_path,
            base_crt_dir=CONF.haproxy_amphora.base_cert_dir,
            haproxy_template=CONF.haproxy_amphora.haproxy_template)

    def update(self, listener, vip):
        LOG.debug("Amphora %s haproxy, updating listener %s, vip %s",
                  self.__class__.__name__, listener.protocol_port,
                  vip.ip_address)

        # Process listener certificate info
        certs = self._process_tls_certificates(listener)

        # Generate HaProxy configuration from listener object
        config = self.jinja.build_config(listener, certs['tls_cert'],
                                         certs['sni_certs'])

        for amp in listener.load_balancer.amphorae:
            if amp.status != constants.DELETED:
                self.client.upload_config(amp, listener.id, config)
                # todo (german): add a method to REST interface to reload or
                #                start without having to check
                # Is that listener running?
                r = self.client.get_listener_status(amp,
                                                    listener.id)
                if r['status'] == 'ACTIVE':
                    self.client.reload_listener(amp, listener.id)
                else:
                    self.client.start_listener(amp, listener.id)

    def _apply(self, func, listener=None, *args):
        for amp in listener.load_balancer.amphorae:
            if amp.status != constants.DELETED:
                func(amp, listener.id, *args)

    def stop(self, listener, vip):
        self._apply(self.client.stop_listener, listener)

    def start(self, listener, vip):
        self._apply(self.client.start_listener, listener)

    def delete(self, listener, vip):
        self._apply(self.client.delete_listener, listener)

    def get_info(self, amphora):
        self.driver.get_info(amphora.lb_network_ip)

    def get_diagnostics(self, amphora):
        self.driver.get_diagnostics(amphora.lb_network_ip)

    def finalize_amphora(self, amphora):
        pass

    def post_vip_plug(self, load_balancer, amphorae_network_config):
        for amp in load_balancer.amphorae:
            if amp.status != constants.DELETED:
                subnet = amphorae_network_config.get(amp.id).vip_subnet
                # NOTE(blogan): using the vrrp port here because that
                # is what the allowed address pairs network driver sets
                # this particular port to.  This does expose a bit of
                # tight coupling between the network driver and amphora
                # driver.  We will need to revisit this to try and remove
                # this tight coupling.
                port = amphorae_network_config.get(amp.id).vrrp_port
                net_info = {'subnet_cidr': subnet.cidr,
                            'gateway': subnet.gateway_ip,
                            'mac_address': port.mac_address}
                self.client.plug_vip(amp,
                                     load_balancer.vip.ip_address,
                                     net_info)

    def post_network_plug(self, amphora, port):
        port_info = {'mac_address': port.mac_address}
        self.client.plug_network(amphora, port_info)

    def _process_tls_certificates(self, listener):
        """Processes TLS data from the listener.

        Converts and uploads PEM data to the Amphora API

        return TLS_CERT and SNI_CERTS
        """
        tls_cert = None
        sni_certs = []

        certs = []

        if listener.tls_certificate_id:
            tls_cert = self._map_cert_tls_container(
                self.cert_manager.get_cert(listener.tls_certificate_id))
            certs.append(tls_cert)
        if listener.sni_containers:
            for sni_cont in listener.sni_containers:
                bbq_container = self._map_cert_tls_container(
                    self.cert_manager.get_cert(sni_cont.tls_container.id))
                sni_certs.append(bbq_container)
                certs.append(bbq_container)

        for cert in certs:
            pem = self._build_pem(cert)
            md5 = hashlib.md5(pem).hexdigest()
            name = '{cn}.pem'.format(cn=cert.primary_cn)
            self._apply(self._upload_cert, listener, pem, md5, name)

        return {'tls_cert': tls_cert, 'sni_certs': sni_certs}

    def _upload_cert(self, amp, listener_id, pem, md5, name):
        try:
            if self.client.get_cert_md5sum(amp, listener_id, name) == md5:
                return
        except exc.NotFound:
            pass

        self.client.upload_cert_pem(
            amp, listener_id, name, pem)

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
        map(six.b, pem)

        return six.b('\n').join(pem)


# Check a custom hostname
class CustomHostNameCheckingAdapter(requests.adapters.HTTPAdapter):
    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self.uuid
        return super(CustomHostNameCheckingAdapter,
                     self).cert_verify(conn, url, verify, cert)


class AmphoraAPIClient(object):
    def __init__(self):
        super(AmphoraAPIClient, self).__init__()
        self.secure = False

        self.get = functools.partial(self.request, 'get')
        self.post = functools.partial(self.request, 'post')
        self.put = functools.partial(self.request, 'put')
        self.delete = functools.partial(self.request, 'delete')
        self.head = functools.partial(self.request, 'head')

        self.start_listener = functools.partial(self._action, 'start')
        self.stop_listener = functools.partial(self._action, 'stop')
        self.reload_listener = functools.partial(self._action, 'reload')

        self.session = requests.Session()
        self.session.cert = CONF.haproxy_amphora.client_cert
        self.ssl_adapter = CustomHostNameCheckingAdapter()
        self.session.mount('https://', self.ssl_adapter)

    def _base_url(self, ip):
        return "https://{ip}:{port}/{version}/".format(
            ip=ip,
            port=CONF.haproxy_amphora.bind_port,
            version=API_VERSION)

    def request(self, method, amp, path='/', **kwargs):
        LOG.debug("request url " + path)
        _request = getattr(self.session, method.lower())
        _url = self._base_url(amp.lb_network_ip) + path

        reqargs = {
            'verify': CONF.haproxy_amphora.server_ca,
            'url': _url, }
        reqargs.update(kwargs)
        headers = reqargs.setdefault('headers', {})

        headers['User-Agent'] = OCTAVIA_API_CLIENT
        self.ssl_adapter.uuid = amp.id
        # Keep retrying
        for a in six.moves.xrange(CONF.haproxy_amphora.connection_max_retries):
            try:
                r = _request(**reqargs)
            except requests.ConnectionError:
                LOG.warn(_LW("Could not talk  to instance"))
                time.sleep(CONF.haproxy_amphora.connection_retry_interval)
                if a >= CONF.haproxy_amphora.connection_max_retries:
                    raise driver_except.TimeOutException()
            else:
                return r
        raise driver_except.UnavailableException()

    def upload_config(self, amp, listener_id, config):
        r = self.put(
            amp,
            'listeners/{listener_id}/haproxy'.format(listener_id=listener_id),
            data=config)
        return exc.check_exception(r)

    def get_listener_status(self, amp, listener_id):
        r = self.get(
            amp,
            'listeners/{listener_id}'.format(listener_id=listener_id))
        if exc.check_exception(r):
            return r.json()

    def _action(self, action, amp, listener_id):
        r = self.put(amp, 'listeners/{listener_id}/{action}'.format(
            listener_id=listener_id, action=action))
        return exc.check_exception(r)

    def upload_cert_pem(self, amp, listener_id, pem_filename, pem_file):
        r = self.put(
            amp,
            'listeners/{listener_id}/certificates/{filename}'.format(
                listener_id=listener_id, filename=pem_filename),
            data=pem_file)
        return exc.check_exception(r)

    def get_cert_md5sum(self, amp, listener_id, pem_filename):
        r = self.get(amp,
                     'listeners/{listener_id}/certificates/{filename}'.format(
                         listener_id=listener_id, filename=pem_filename))
        if exc.check_exception(r):
            return r.json().get("md5sum")

    def delete_listener(self, amp, listener_id):
        r = self.delete(
            amp, 'listeners/{listener_id}'.format(listener_id=listener_id))
        return exc.check_exception(r)

    def get_info(self, amp):
        r = self.get(amp, "info")
        if exc.check_exception(r):
            return r.json()

    def get_details(self, amp):
        r = self.get(amp, "details")
        if exc.check_exception(r):
            return r.json()

    def get_all_listeners(self, amp):
        r = self.get(amp, "listeners")
        if exc.check_exception(r):
            return r.json()

    def delete_cert_pem(self, amp, listener_id, pem_filename):
        r = self.delete(
            amp,
            'listeners/{listener_id}/certificates/{filename}'.format(
                listener_id=listener_id, filename=pem_filename))
        return exc.check_exception(r)

    def plug_network(self, amp, port):
        r = self.post(amp, 'plug/network',
                      json=port)
        return exc.check_exception(r)

    def plug_vip(self, amp, vip, net_info):
        r = self.post(amp,
                      'plug/vip/{vip}'.format(vip=vip),
                      json=net_info)
        return exc.check_exception(r)
