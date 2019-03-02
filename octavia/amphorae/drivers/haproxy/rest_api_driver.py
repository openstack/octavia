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
import os
import time
import warnings

from oslo_context import context as oslo_context
from oslo_log import log as logging
import requests
import simplejson
import six
from stevedore import driver as stevedore_driver

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.amphorae.drivers import driver_base
from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.amphorae.drivers.keepalived import vrrp_rest_driver
from octavia.common.config import cfg
from octavia.common import constants as consts
from octavia.common.jinja.haproxy import jinja_cfg
from octavia.common.jinja.lvs import jinja_cfg as jinja_udp_cfg
from octavia.common.tls_utils import cert_parser
from octavia.common import utils

LOG = logging.getLogger(__name__)
API_VERSION = consts.API_VERSION
OCTAVIA_API_CLIENT = (
    "Octavia HaProxy Rest Client/{version} "
    "(https://wiki.openstack.org/wiki/Octavia)").format(version=API_VERSION)
CONF = cfg.CONF


class HaproxyAmphoraLoadBalancerDriver(
    driver_base.AmphoraLoadBalancerDriver,
        vrrp_rest_driver.KeepalivedAmphoraDriverMixin):

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
            haproxy_template=CONF.haproxy_amphora.haproxy_template,
            connection_logging=CONF.haproxy_amphora.connection_logging)
        self.udp_jinja = jinja_udp_cfg.LvsJinjaTemplater()

    def _get_haproxy_versions(self, amphora):
        """Get major and minor version number from haproxy

        Example: ['1', '6']

        :returns version_list: A list with the major and minor numbers
        """

        version_string = self.client.get_info(amphora)['haproxy_version']

        return version_string.split('.')[:2]

    def update_amphora_listeners(self, listeners, amphora_index,
                                 amphorae, timeout_dict=None):
        """Update the amphora with a new configuration.

        :param listeners: List of listeners to update.
        :type listener: list
        :param amphora_index: The index of the amphora to update
        :type amphora_index: integer
        :param amphorae: List of amphorae
        :type amphorae: list
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :returns: None

        Updates the configuration of the listeners on a single amphora.
        """
        # if the amphora does not yet have listeners, no need to update them.
        if not listeners:
            LOG.debug('No listeners found to update.')
            return
        amp = amphorae[amphora_index]
        if amp is None or amp.status == consts.DELETED:
            return

        haproxy_versions = self._get_haproxy_versions(amp)

        # TODO(johnsom) remove when we don't have a process per listener
        for listener in listeners:
            LOG.debug("%s updating listener %s on amphora %s",
                      self.__class__.__name__, listener.id, amp.id)
            if listener.protocol == 'UDP':
                # Generate Keepalived LVS configuration from listener object
                config = self.udp_jinja.build_config(listener=listener)
                self.client.upload_udp_config(amp, listener.id, config,
                                              timeout_dict=timeout_dict)
                self.client.reload_listener(amp, listener.id,
                                            timeout_dict=timeout_dict)
            else:
                certs = self._process_tls_certificates(listener)
                client_ca_filename = self._process_secret(
                    listener, listener.client_ca_tls_certificate_id)
                crl_filename = self._process_secret(
                    listener, listener.client_crl_container_id)
                pool_tls_certs = self._process_listener_pool_certs(listener)

                # Generate HaProxy configuration from listener object
                config = self.jinja.build_config(
                    host_amphora=amp, listener=listener,
                    tls_cert=certs['tls_cert'],
                    haproxy_versions=haproxy_versions,
                    client_ca_filename=client_ca_filename,
                    client_crl=crl_filename,
                    pool_tls_certs=pool_tls_certs)
                self.client.upload_config(amp, listener.id, config,
                                          timeout_dict=timeout_dict)
                self.client.reload_listener(amp, listener.id,
                                            timeout_dict=timeout_dict)

    def _udp_update(self, listener, vip):
        LOG.debug("Amphora %s keepalivedlvs, updating "
                  "listener %s, vip %s",
                  self.__class__.__name__, listener.protocol_port,
                  vip.ip_address)

        for amp in listener.load_balancer.amphorae:
            if amp.status != consts.DELETED:
                # Generate Keepalived LVS configuration from listener object
                config = self.udp_jinja.build_config(listener=listener)
                self.client.upload_udp_config(amp, listener.id, config)
                self.client.reload_listener(amp, listener.id)

    def update(self, listener, vip):
        if listener.protocol == 'UDP':
            self._udp_update(listener, vip)
        else:
            LOG.debug("Amphora %s haproxy, updating listener %s, "
                      "vip %s", self.__class__.__name__,
                      listener.protocol_port,
                      vip.ip_address)

            # Process listener certificate info
            certs = self._process_tls_certificates(listener)
            client_ca_filename = self._process_secret(
                listener, listener.client_ca_tls_certificate_id)
            crl_filename = self._process_secret(
                listener, listener.client_crl_container_id)
            pool_tls_certs = self._process_listener_pool_certs(listener)

            for amp in listener.load_balancer.amphorae:
                if amp.status != consts.DELETED:

                    haproxy_versions = self._get_haproxy_versions(amp)

                    # Generate HaProxy configuration from listener object
                    config = self.jinja.build_config(
                        host_amphora=amp, listener=listener,
                        tls_cert=certs['tls_cert'],
                        haproxy_versions=haproxy_versions,
                        client_ca_filename=client_ca_filename,
                        client_crl=crl_filename,
                        pool_tls_certs=pool_tls_certs)
                    self.client.upload_config(amp, listener.id, config)
                    self.client.reload_listener(amp, listener.id)

    def upload_cert_amp(self, amp, pem):
        LOG.debug("Amphora %s updating cert in REST driver "
                  "with amphora id %s,",
                  self.__class__.__name__, amp.id)
        self.client.update_cert_for_rotation(amp, pem)

    def _apply(self, func, listener=None, amphora=None, *args):
        if amphora is None:
            for amp in listener.load_balancer.amphorae:
                if amp.status != consts.DELETED:
                    func(amp, listener.id, *args)
        else:
            if amphora.status != consts.DELETED:
                func(amphora, listener.id, *args)

    def stop(self, listener, vip):
        self._apply(self.client.stop_listener, listener)

    def start(self, listener, vip, amphora=None):
        self._apply(self.client.start_listener, listener, amphora)

    def delete(self, listener, vip):
        self._apply(self.client.delete_listener, listener)

    def get_info(self, amphora):
        return self.client.get_info(amphora)

    def get_diagnostics(self, amphora):
        pass

    def finalize_amphora(self, amphora):
        pass

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config):
        if amphora.status != consts.DELETED:
            subnet = amphorae_network_config.get(amphora.id).vip_subnet
            # NOTE(blogan): using the vrrp port here because that
            # is what the allowed address pairs network driver sets
            # this particular port to.  This does expose a bit of
            # tight coupling between the network driver and amphora
            # driver.  We will need to revisit this to try and remove
            # this tight coupling.
            # NOTE (johnsom): I am loading the vrrp_ip into the
            # net_info structure here so that I don't break
            # compatibility with old amphora agent versions.

            port = amphorae_network_config.get(amphora.id).vrrp_port
            LOG.debug("Post-VIP-Plugging with vrrp_ip %s vrrp_port %s",
                      amphora.vrrp_ip, port.id)
            host_routes = [{'nexthop': hr.nexthop,
                            'destination': hr.destination}
                           for hr in subnet.host_routes]
            net_info = {'subnet_cidr': subnet.cidr,
                        'gateway': subnet.gateway_ip,
                        'mac_address': port.mac_address,
                        'vrrp_ip': amphora.vrrp_ip,
                        'mtu': port.network.mtu,
                        'host_routes': host_routes}
            try:
                self.client.plug_vip(amphora,
                                     load_balancer.vip.ip_address,
                                     net_info)
            except exc.Conflict:
                LOG.warning('VIP with MAC %(mac)s already exists on amphora, '
                            'skipping post_vip_plug',
                            {'mac': port.mac_address})

    def post_network_plug(self, amphora, port):
        fixed_ips = []
        for fixed_ip in port.fixed_ips:
            host_routes = [{'nexthop': hr.nexthop,
                            'destination': hr.destination}
                           for hr in fixed_ip.subnet.host_routes]
            ip = {'ip_address': fixed_ip.ip_address,
                  'subnet_cidr': fixed_ip.subnet.cidr,
                  'host_routes': host_routes}
            fixed_ips.append(ip)
        port_info = {'mac_address': port.mac_address,
                     'fixed_ips': fixed_ips,
                     'mtu': port.network.mtu}
        try:
            self.client.plug_network(amphora, port_info)
        except exc.Conflict:
            LOG.warning('Network with MAC %(mac)s already exists on amphora, '
                        'skipping post_network_plug',
                        {'mac': port.mac_address})

    def _process_tls_certificates(self, listener):
        """Processes TLS data from the listener.

        Converts and uploads PEM data to the Amphora API

        return TLS_CERT and SNI_CERTS
        """
        tls_cert = None
        sni_certs = []
        certs = []

        data = cert_parser.load_certificates_data(
            self.cert_manager, listener)
        if data['tls_cert'] is not None:
            tls_cert = data['tls_cert']
            certs.append(tls_cert)
        if data['sni_certs']:
            sni_certs = data['sni_certs']
            certs.extend(sni_certs)

        for cert in certs:
            pem = cert_parser.build_pem(cert)
            md5 = hashlib.md5(pem).hexdigest()  # nosec
            name = '{id}.pem'.format(id=cert.id)
            self._apply(self._upload_cert, listener, None, pem, md5, name)

        return {'tls_cert': tls_cert, 'sni_certs': sni_certs}

    def _process_secret(self, listener, secret_ref):
        """Get the secret from the cert manager and upload it to the amp.

        :returns: The filename of the secret in the amp.
        """
        if not secret_ref:
            return None
        context = oslo_context.RequestContext(project_id=listener.project_id)
        secret = self.cert_manager.get_secret(context, secret_ref)
        try:
            secret = secret.encode('utf-8')
        except AttributeError:
            pass
        md5 = hashlib.md5(secret).hexdigest()  # nosec
        id = hashlib.sha1(secret).hexdigest()  # nosec
        name = '{id}.pem'.format(id=id)
        self._apply(self._upload_cert, listener, None, secret, md5, name)
        return name

    def _process_listener_pool_certs(self, listener):
        #     {'POOL-ID': {
        #         'client_cert': client_full_filename,
        #         'ca_cert': ca_cert_full_filename,
        #         'crl': crl_full_filename}}
        pool_certs_dict = dict()
        for pool in listener.pools:
            if pool.id not in pool_certs_dict:
                pool_certs_dict[pool.id] = self._process_pool_certs(listener,
                                                                    pool)
        for l7policy in listener.l7policies:
            if (l7policy.redirect_pool and
                    l7policy.redirect_pool.id not in pool_certs_dict):
                pool_certs_dict[l7policy.redirect_pool.id] = (
                    self._process_pool_certs(listener, l7policy.redirect_pool))
        return pool_certs_dict

    def _process_pool_certs(self, listener, pool):
        pool_cert_dict = dict()

        # Handle the cleint cert(s) and key
        if pool.tls_certificate_id:
            data = cert_parser.load_certificates_data(self.cert_manager, pool)
            pem = cert_parser.build_pem(data)
            try:
                pem = pem.encode('utf-8')
            except AttributeError:
                pass
            md5 = hashlib.md5(pem).hexdigest()  # nosec
            name = '{id}.pem'.format(id=data.id)
            self._apply(self._upload_cert, listener, None, pem, md5, name)
            pool_cert_dict['client_cert'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, listener.id, name)
        if pool.ca_tls_certificate_id:
            name = self._process_secret(listener, pool.ca_tls_certificate_id)
            pool_cert_dict['ca_cert'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, listener.id, name)
        if pool.crl_container_id:
            name = self._process_secret(listener, pool.crl_container_id)
            pool_cert_dict['crl'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, listener.id, name)

        return pool_cert_dict

    def _upload_cert(self, amp, listener_id, pem, md5, name):
        try:
            if self.client.get_cert_md5sum(
                    amp, listener_id, name, ignore=(404,)) == md5:
                return
        except exc.NotFound:
            pass

        self.client.upload_cert_pem(amp, listener_id, name, pem)

    def update_amphora_agent_config(self, amphora, agent_config,
                                    timeout_dict=None):
        """Update the amphora agent configuration file.

        :param amphora: The amphora to update.
        :type amphora: object
        :param agent_config: The new amphora agent configuration.
        :type agent_config: string
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :returns: None

        Note: This will mutate the amphora agent config and adopt the
              new values.
        """
        try:
            self.client.update_agent_config(amphora, agent_config,
                                            timeout_dict=timeout_dict)
        except exc.NotFound:
            LOG.debug('Amphora {} does not support the update_agent_config '
                      'API.'.format(amphora.id))
            raise driver_except.AmpDriverNotImplementedError()


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

        self.start_listener = functools.partial(self._action,
                                                consts.AMP_ACTION_START)
        self.stop_listener = functools.partial(self._action,
                                               consts.AMP_ACTION_STOP)
        self.reload_listener = functools.partial(self._action,
                                                 consts.AMP_ACTION_RELOAD)

        self.start_vrrp = functools.partial(self._vrrp_action,
                                            consts.AMP_ACTION_START)
        self.stop_vrrp = functools.partial(self._vrrp_action,
                                           consts.AMP_ACTION_STOP)
        self.reload_vrrp = functools.partial(self._vrrp_action,
                                             consts.AMP_ACTION_RELOAD)

        self.session = requests.Session()
        self.session.cert = CONF.haproxy_amphora.client_cert
        self.ssl_adapter = CustomHostNameCheckingAdapter()
        self.session.mount('https://', self.ssl_adapter)

    def _base_url(self, ip):
        if utils.is_ipv6_lla(ip):
            ip = '[{ip}%{interface}]'.format(
                ip=ip,
                interface=CONF.haproxy_amphora.lb_network_interface)
        elif utils.is_ipv6(ip):
            ip = '[{ip}]'.format(ip=ip)
        return "https://{ip}:{port}/{version}/".format(
            ip=ip,
            port=CONF.haproxy_amphora.bind_port,
            version=API_VERSION)

    def request(self, method, amp, path='/', timeout_dict=None, **kwargs):
        cfg_ha_amp = CONF.haproxy_amphora
        if timeout_dict is None:
            timeout_dict = {}
        req_conn_timeout = timeout_dict.get(
            consts.REQ_CONN_TIMEOUT, cfg_ha_amp.rest_request_conn_timeout)
        req_read_timeout = timeout_dict.get(
            consts.REQ_READ_TIMEOUT, cfg_ha_amp.rest_request_read_timeout)
        conn_max_retries = timeout_dict.get(
            consts.CONN_MAX_RETRIES, cfg_ha_amp.connection_max_retries)
        conn_retry_interval = timeout_dict.get(
            consts.CONN_RETRY_INTERVAL, cfg_ha_amp.connection_retry_interval)

        LOG.debug("request url %s", path)
        _request = getattr(self.session, method.lower())
        _url = self._base_url(amp.lb_network_ip) + path
        LOG.debug("request url %s", _url)
        reqargs = {
            'verify': CONF.haproxy_amphora.server_ca,
            'url': _url,
            'timeout': (req_conn_timeout, req_read_timeout), }
        reqargs.update(kwargs)
        headers = reqargs.setdefault('headers', {})

        headers['User-Agent'] = OCTAVIA_API_CLIENT
        self.ssl_adapter.uuid = amp.id
        exception = None
        # Keep retrying
        for a in six.moves.xrange(conn_max_retries):
            try:
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="A true SSLContext object is not available"
                    )
                    r = _request(**reqargs)
                LOG.debug('Connected to amphora. Response: %(resp)s',
                          {'resp': r})

                content_type = r.headers.get('content-type', '')
                # Check the 404 to see if it is just that the network in the
                # amphora is not yet up, in which case retry.
                # Otherwise return the response quickly.
                if r.status_code == 404:
                    LOG.debug('Got a 404 (content-type: %(content_type)s) -- '
                              'connection data: %(content)s',
                              {'content_type': content_type,
                               'content': r.content})
                    if content_type.find("application/json") == -1:
                        LOG.debug("Amphora agent not ready.")
                        raise requests.ConnectionError
                    try:
                        json_data = r.json().get('details', '')
                        if 'No suitable network interface found' in json_data:
                            LOG.debug("Amphora network interface not found.")
                            raise requests.ConnectionError
                    except simplejson.JSONDecodeError:  # if r.json() fails
                        pass  # TODO(rm_work) Should we do something?
                return r
            except (requests.ConnectionError, requests.Timeout) as e:
                exception = e
                LOG.warning("Could not connect to instance. Retrying.")
                time.sleep(conn_retry_interval)

        LOG.error("Connection retries (currently set to %(max_retries)s) "
                  "exhausted.  The amphora is unavailable. Reason: "
                  "%(exception)s",
                  {'max_retries': conn_max_retries,
                   'exception': exception})
        raise driver_except.TimeOutException()

    def upload_config(self, amp, listener_id, config, timeout_dict=None):
        r = self.put(
            amp,
            'listeners/{amphora_id}/{listener_id}/haproxy'.format(
                amphora_id=amp.id, listener_id=listener_id), timeout_dict,
            data=config)
        return exc.check_exception(r)

    def get_listener_status(self, amp, listener_id):
        r = self.get(
            amp,
            'listeners/{listener_id}'.format(listener_id=listener_id))
        if exc.check_exception(r):
            return r.json()
        return None

    def _action(self, action, amp, listener_id, timeout_dict=None):
        r = self.put(amp, 'listeners/{listener_id}/{action}'.format(
            listener_id=listener_id, action=action), timeout_dict=timeout_dict)
        return exc.check_exception(r)

    def upload_cert_pem(self, amp, listener_id, pem_filename, pem_file):
        r = self.put(
            amp, 'listeners/{listener_id}/certificates/{filename}'.format(
                listener_id=listener_id, filename=pem_filename),
            data=pem_file)
        return exc.check_exception(r)

    def get_cert_md5sum(self, amp, listener_id, pem_filename, ignore=tuple()):
        r = self.get(
            amp, 'listeners/{listener_id}/certificates/{filename}'.format(
                listener_id=listener_id, filename=pem_filename))
        if exc.check_exception(r, ignore):
            return r.json().get("md5sum")
        return None

    def delete_cert_pem(self, amp, listener_id, pem_filename):
        r = self.delete(
            amp, 'listeners/{listener_id}/certificates/{filename}'.format(
                listener_id=listener_id, filename=pem_filename))
        return exc.check_exception(r, (404,))

    def update_cert_for_rotation(self, amp, pem_file):
        r = self.put(amp, 'certificate', data=pem_file)
        return exc.check_exception(r)

    def delete_listener(self, amp, listener_id):
        r = self.delete(
            amp, 'listeners/{listener_id}'.format(listener_id=listener_id))
        return exc.check_exception(r, (404,))

    def get_info(self, amp):
        r = self.get(amp, "info")
        if exc.check_exception(r):
            return r.json()
        return None

    def get_details(self, amp):
        r = self.get(amp, "details")
        if exc.check_exception(r):
            return r.json()
        return None

    def get_all_listeners(self, amp):
        r = self.get(amp, "listeners")
        if exc.check_exception(r):
            return r.json()
        return None

    def plug_network(self, amp, port):
        r = self.post(amp, 'plug/network',
                      json=port)
        return exc.check_exception(r)

    def plug_vip(self, amp, vip, net_info):
        r = self.post(amp,
                      'plug/vip/{vip}'.format(vip=vip),
                      json=net_info)
        return exc.check_exception(r)

    def upload_vrrp_config(self, amp, config):
        r = self.put(amp, 'vrrp/upload', data=config)
        return exc.check_exception(r)

    def _vrrp_action(self, action, amp):
        r = self.put(amp, 'vrrp/{action}'.format(action=action))
        return exc.check_exception(r)

    def get_interface(self, amp, ip_addr, timeout_dict=None):
        r = self.get(amp, 'interface/{ip_addr}'.format(ip_addr=ip_addr),
                     timeout_dict=timeout_dict)
        if exc.check_exception(r):
            return r.json()
        return None

    def upload_udp_config(self, amp, listener_id, config, timeout_dict=None):
        r = self.put(
            amp,
            'listeners/{amphora_id}/{listener_id}/udp_listener'.format(
                amphora_id=amp.id, listener_id=listener_id), timeout_dict,
            data=config)
        return exc.check_exception(r)

    def update_agent_config(self, amp, agent_config, timeout_dict=None):
        r = self.put(amp, 'config', timeout_dict, data=agent_config)
        return exc.check_exception(r)
