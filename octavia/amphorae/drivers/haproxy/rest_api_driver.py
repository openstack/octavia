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
import ssl
import time
from typing import Optional
import warnings

from oslo_context import context as oslo_context
from oslo_log import log as logging
from oslo_utils.secretutils import md5
import requests
import simplejson
from stevedore import driver as stevedore_driver

from octavia.amphorae.driver_exceptions import exceptions as driver_except
from octavia.amphorae.drivers import driver_base
from octavia.amphorae.drivers.haproxy import exceptions as exc
from octavia.amphorae.drivers.keepalived import vrrp_rest_driver
from octavia.common.config import cfg
from octavia.common import constants as consts
import octavia.common.jinja.haproxy.combined_listeners.jinja_cfg as jinja_combo
from octavia.common.jinja.lvs import jinja_cfg as jinja_udp_cfg
from octavia.common.tls_utils import cert_parser
from octavia.common import utils
from octavia.db import api as db_api
from octavia.db import models as db_models
from octavia.db import repositories as repo


LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class HaproxyAmphoraLoadBalancerDriver(
    driver_base.AmphoraLoadBalancerDriver,
        vrrp_rest_driver.KeepalivedAmphoraDriverMixin):

    def __init__(self):
        super().__init__()
        self.clients = {
            'base': AmphoraAPIClientBase(),
            '1.0': AmphoraAPIClient1_0(),
        }
        self.cert_manager = stevedore_driver.DriverManager(
            namespace='octavia.cert_manager',
            name=CONF.certificates.cert_manager,
            invoke_on_load=True,
        ).driver

        self.jinja_combo = jinja_combo.JinjaTemplater(
            base_amp_path=CONF.haproxy_amphora.base_path,
            base_crt_dir=CONF.haproxy_amphora.base_cert_dir,
            haproxy_template=CONF.haproxy_amphora.haproxy_template,
            connection_logging=CONF.haproxy_amphora.connection_logging)
        self.lvs_jinja = jinja_udp_cfg.LvsJinjaTemplater()

    def _get_haproxy_versions(self, amphora, timeout_dict=None):
        """Get major and minor version number from haproxy

        Example: ['1', '6']

        :returns version_list: A list with the major and minor numbers
        """
        self._populate_amphora_api_version(
            amphora, timeout_dict=timeout_dict)
        amp_info = self.clients[amphora.api_version].get_info(
            amphora, timeout_dict=timeout_dict)
        haproxy_version_string = amp_info['haproxy_version']

        return haproxy_version_string.split('.')[:2]

    def _populate_amphora_api_version(self, amphora, timeout_dict=None,
                                      raise_retry_exception=False):
        """Populate the amphora object with the api_version

        This will query the amphora for version discovery and populate
        the api_version string attribute on the amphora object.

        :returns: None
        """
        if not getattr(amphora, 'api_version', None):
            try:
                amphora.api_version = self.clients['base'].get_api_version(
                    amphora, timeout_dict=timeout_dict,
                    raise_retry_exception=raise_retry_exception)['api_version']
            except exc.NotFound:
                # Amphora is too old for version discovery, default to 0.5
                amphora.api_version = '0.5'
        LOG.debug('Amphora %s has API version %s',
                  amphora.id, amphora.api_version)
        api_version = list(map(int, amphora.api_version.split('.')))

        if api_version[0] == 0 and api_version[1] <= 5:  # 0.5 or earlier
            raise driver_except.AmpVersionUnsupported(
                version=amphora.api_version)

        return api_version

    def update_amphora_listeners(self, loadbalancer, amphora,
                                 timeout_dict=None):
        """Update the amphora with a new configuration.

        :param loadbalancer: The load balancer to update
        :type loadbalancer: object
        :param amphora: The amphora to update
        :type amphora: object
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :returns: None

        Updates the configuration of the listeners on a single amphora.
        """
        # if the amphora does not yet have listeners, no need to update them.
        if not loadbalancer.listeners:
            LOG.debug('No listeners found to update.')
            return
        if amphora is None or amphora.status == consts.DELETED:
            return

        # Check which HAProxy version is on the amp
        haproxy_versions = self._get_haproxy_versions(
            amphora, timeout_dict=timeout_dict)
        # Check if version is supported
        self._populate_amphora_api_version(amphora)

        has_tcp = False
        certs = {}
        listeners_to_update = []
        for listener in loadbalancer.listeners:
            LOG.debug("%s updating listener %s on amphora %s",
                      self.__class__.__name__, listener.id, amphora.id)
            if listener.protocol in consts.LVS_PROTOCOLS:
                # Generate Keepalived LVS configuration from listener object
                config = self.lvs_jinja.build_config(listener=listener)
                self.clients[amphora.api_version].upload_udp_config(
                    amphora, listener.id, config, timeout_dict=timeout_dict)
                self.clients[amphora.api_version].reload_listener(
                    amphora, listener.id, timeout_dict=timeout_dict)
            else:
                has_tcp = True
                obj_id = loadbalancer.id

                try:
                    certs.update({
                        listener.tls_certificate_id:
                        self._process_tls_certificates(
                            listener, amphora, obj_id)['tls_cert']})
                    certs.update({listener.client_ca_tls_certificate_id:
                                  self._process_secret(
                                      listener,
                                      listener.client_ca_tls_certificate_id,
                                      amphora, obj_id)})
                    certs.update({listener.client_crl_container_id:
                                  self._process_secret(
                                      listener,
                                      listener.client_crl_container_id,
                                      amphora, obj_id)})

                    certs.update(self._process_listener_pool_certs(
                        listener, amphora, obj_id))

                    listeners_to_update.append(listener)
                except Exception as e:
                    LOG.exception('Unable to update listener %s due to '
                                  '"%s". Skipping this listener.',
                                  listener.id, str(e))
                    listener_repo = repo.ListenerRepository()
                    with db_api.session().begin() as session:
                        listener_repo.update(session, listener.id,
                                             provisioning_status=consts.ERROR,
                                             operating_status=consts.ERROR)

        if has_tcp:
            if listeners_to_update:
                # Generate HaProxy configuration from listener object
                amp_details = self.clients[amphora.api_version].get_details(
                    amphora)
                config = self.jinja_combo.build_config(
                    host_amphora=amphora, listeners=listeners_to_update,
                    tls_certs=certs,
                    haproxy_versions=haproxy_versions,
                    amp_details=amp_details)
                self.clients[amphora.api_version].upload_config(
                    amphora, loadbalancer.id, config,
                    timeout_dict=timeout_dict)
                self.clients[amphora.api_version].reload_listener(
                    amphora, loadbalancer.id, timeout_dict=timeout_dict)
            else:
                # If we aren't updating any listeners, make sure there are
                # no listeners hanging around. For example if this update
                # was called from a listener delete.
                self.clients[amphora.api_version].delete_listener(
                    amphora, loadbalancer.id)

    def _udp_update(self, listener, vip):
        LOG.debug("Amphora %s keepalivedlvs, updating "
                  "listener %s, vip %s",
                  self.__class__.__name__, listener.protocol_port,
                  vip.ip_address)

        for amp in listener.load_balancer.amphorae:
            if amp.status != consts.DELETED:
                # Generate Keepalived LVS configuration from listener object
                self._populate_amphora_api_version(amp)
                config = self.lvs_jinja.build_config(listener=listener)
                self.clients[amp.api_version].upload_udp_config(
                    amp, listener.id, config)
                self.clients[amp.api_version].reload_listener(
                    amp, listener.id)

    def update(self, loadbalancer):
        for amphora in loadbalancer.amphorae:
            if amphora.status != consts.DELETED:
                self.update_amphora_listeners(loadbalancer, amphora)

    def upload_cert_amp(self, amp, pem):
        LOG.debug("Amphora %s updating cert in REST driver "
                  "with amphora id %s,",
                  self.__class__.__name__, amp.id)
        self._populate_amphora_api_version(amp)
        self.clients[amp.api_version].update_cert_for_rotation(amp, pem)

    def _apply(self, func_name, loadbalancer, amphora=None, *args, **kwargs):
        if amphora is None:
            amphorae = loadbalancer.amphorae
        else:
            amphorae = [amphora]

        for amp in amphorae:
            if amp.status != consts.DELETED:
                self._populate_amphora_api_version(
                    amp, timeout_dict=args[0])
                has_tcp = False
                for listener in loadbalancer.listeners:
                    if listener.protocol in consts.LVS_PROTOCOLS:
                        getattr(self.clients[amp.api_version], func_name)(
                            amp, listener.id, *args)
                    else:
                        has_tcp = True
                if has_tcp:
                    getattr(self.clients[amp.api_version], func_name)(
                        amp, loadbalancer.id, *args)

    def reload(self, loadbalancer, amphora=None, timeout_dict=None):
        self._apply('reload_listener', loadbalancer, amphora, timeout_dict)

    def start(self, loadbalancer, amphora=None, timeout_dict=None):
        self._apply('start_listener', loadbalancer, amphora, timeout_dict)

    def delete(self, listener):
        # Delete any UDP/SCTP listeners the old way (we didn't update the way
        # they are configured)
        loadbalancer = listener.load_balancer
        if listener.protocol in consts.LVS_PROTOCOLS:
            for amp in loadbalancer.amphorae:
                if amp.status != consts.DELETED:
                    self._populate_amphora_api_version(amp)
                    self.clients[amp.api_version].delete_listener(
                        amp, listener.id)
            return

        # In case the listener is not UDP or SCTP, things get more complicated.
        for amp in loadbalancer.amphorae:
            if amp.status != consts.DELETED:
                self._combined_config_delete(amp, listener)

    def _combined_config_delete(self, amphora, listener):
        # Remove the listener from the listener list on the LB before
        # passing the whole thing over to update (so it'll actually delete)
        # In case of amphorae in ACTIVE_STANDBY topology, ensure that we don't
        # remove an already removed listener.
        if listener in listener.load_balancer.listeners:
            listener.load_balancer.listeners.remove(listener)

        # Check if there's any certs that we need to delete
        certs = self._process_tls_certificates(listener)
        certs_to_delete = set()
        if certs['tls_cert']:
            certs_to_delete.add(certs['tls_cert'].id)
        for sni_cert in certs['sni_certs']:
            certs_to_delete.add(sni_cert.id)

        # Delete them (they'll be recreated before the reload if they are
        # needed for other listeners anyway)
        self._populate_amphora_api_version(amphora)
        for cert_id in certs_to_delete:
            self.clients[amphora.api_version].delete_cert_pem(
                amphora, listener.load_balancer.id,
                '{id}.pem'.format(id=cert_id))

        # See how many non-UDP/SCTP listeners we have left
        non_lvs_listener_count = len([
            1 for li in listener.load_balancer.listeners
            if li.protocol not in consts.LVS_PROTOCOLS])
        if non_lvs_listener_count > 0:
            # We have other listeners, so just update is fine.
            # TODO(rm_work): This is a little inefficient since this duplicates
            # a lot of the detection logic that has already been done, but it
            # is probably safer to re-use the existing code-path.
            self.update_amphora_listeners(listener.load_balancer, amphora)
        else:
            # Deleting the last listener, so really do the delete
            self.clients[amphora.api_version].delete_listener(
                amphora, listener.load_balancer.id)

    def get_info(self, amphora, raise_retry_exception=False,
                 timeout_dict=None):
        self._populate_amphora_api_version(
            amphora, raise_retry_exception=raise_retry_exception,
            timeout_dict=timeout_dict)
        return self.clients[amphora.api_version].get_info(
            amphora, raise_retry_exception=raise_retry_exception,
            timeout_dict=timeout_dict)

    def get_diagnostics(self, amphora):
        pass

    def finalize_amphora(self, amphora):
        pass

    def _build_net_info(self, port, amphora, subnet, mtu=None):
        # NOTE(blogan): using the vrrp port here because that
        # is what the allowed address pairs network driver sets
        # this particular port to.  This does expose a bit of
        # tight coupling between the network driver and amphora
        # driver.  We will need to revisit this to try and remove
        # this tight coupling.
        # NOTE (johnsom): I am loading the vrrp_ip into the
        # net_info structure here so that I don't break
        # compatibility with old amphora agent versions.
        host_routes = [{'nexthop': hr[consts.NEXTHOP],
                        'destination': hr[consts.DESTINATION]}
                       for hr in subnet[consts.HOST_ROUTES]]
        net_info = {'subnet_cidr': subnet[consts.CIDR],
                    'gateway': subnet[consts.GATEWAY_IP],
                    'mac_address': port[consts.MAC_ADDRESS],
                    'vrrp_ip': amphora[consts.VRRP_IP],
                    'mtu': mtu or port[consts.NETWORK][consts.MTU],
                    'host_routes': host_routes,
                    'additional_vips': []}
        return net_info

    def post_vip_plug(self, amphora, load_balancer, amphorae_network_config,
                      vrrp_port, vip_subnet, additional_vip_data=None):
        if amphora.status != consts.DELETED:
            self._populate_amphora_api_version(amphora)
            port = vrrp_port.to_dict(recurse=True)
            mtu = port[consts.NETWORK][consts.MTU]
            LOG.debug("Post-VIP-Plugging with vrrp_ip %s vrrp_port %s",
                      amphora.vrrp_ip, port[consts.ID])
            net_info = self._build_net_info(
                port, amphora.to_dict(),
                vip_subnet.to_dict(recurse=True), mtu)
            for add_vip in additional_vip_data:
                add_host_routes = [{'nexthop': hr.nexthop,
                                    'destination': hr.destination}
                                   for hr in add_vip.subnet.host_routes]
                add_net_info = {'subnet_cidr': add_vip.subnet.cidr,
                                'ip_address': add_vip.ip_address,
                                'gateway': add_vip.subnet.gateway_ip,
                                'host_routes': add_host_routes}
                net_info['additional_vips'].append(add_net_info)
            try:
                self.clients[amphora.api_version].plug_vip(
                    amphora, load_balancer.vip.ip_address, net_info)
            except exc.Conflict:
                LOG.warning('VIP with MAC %(mac)s already exists on amphora, '
                            'skipping post_vip_plug',
                            {'mac': port[consts.MAC_ADDRESS]})

    def post_network_plug(self, amphora, port, amphora_network_config):
        fixed_ips = []
        for fixed_ip in port.fixed_ips:
            host_routes = [{'nexthop': hr.nexthop,
                            'destination': hr.destination}
                           for hr in fixed_ip.subnet.host_routes]
            ip = {'ip_address': fixed_ip.ip_address,
                  'subnet_cidr': fixed_ip.subnet.cidr,
                  'host_routes': host_routes,
                  'gateway': fixed_ip.subnet.gateway_ip}
            fixed_ips.append(ip)
        port_info = {'mac_address': port.mac_address,
                     'fixed_ips': fixed_ips,
                     'mtu': port.network.mtu}
        if port.id == amphora.vrrp_port_id:
            # We have to special-case sharing the vrrp port and pass through
            # enough extra information to populate the whole VIP port
            net_info = self._build_net_info(
                port.to_dict(recurse=True), amphora.to_dict(),
                amphora_network_config[consts.VIP_SUBNET],
                port.network.mtu)
            net_info['vip'] = amphora.ha_ip
            port_info['vip_net_info'] = net_info
        try:
            self._populate_amphora_api_version(amphora)
            self.clients[amphora.api_version].plug_network(amphora, port_info)
        except exc.Conflict:
            LOG.warning('Network with MAC %(mac)s already exists on amphora, '
                        'skipping post_network_plug',
                        {'mac': port.mac_address})

    def _process_tls_certificates(self, listener, amphora=None, obj_id=None):
        """Processes TLS data from the listener.

        Converts and uploads PEM data to the Amphora API

        return TLS_CERT and SNI_CERTS
        """
        tls_cert = None
        sni_certs = []
        certs = []
        cert_filename_list = []

        data = cert_parser.load_certificates_data(
            self.cert_manager, listener)
        if data['tls_cert'] is not None:
            tls_cert = data['tls_cert']
            # Note, the first cert is the TLS default cert
            certs.append(tls_cert)
        if data['sni_certs']:
            sni_certs = data['sni_certs']
            certs.extend(sni_certs)

        if amphora and obj_id:
            for cert in certs:
                pem = cert_parser.build_pem(cert)
                md5sum = md5(pem, usedforsecurity=False).hexdigest()  # nosec
                name = '{id}.pem'.format(id=cert.id)
                cert_filename_list.append(
                    os.path.join(
                        CONF.haproxy_amphora.base_cert_dir, obj_id, name))
                self._upload_cert(amphora, obj_id, pem, md5sum, name)

            if certs:
                # Build and upload the crt-list file for haproxy
                crt_list = "\n".join(cert_filename_list)
                crt_list = f'{crt_list}\n'.encode('utf-8')
                md5sum = md5(crt_list,
                             usedforsecurity=False).hexdigest()  # nosec
                name = '{id}.pem'.format(id=listener.id)
                self._upload_cert(amphora, obj_id, crt_list, md5sum, name)
        return {'tls_cert': tls_cert, 'sni_certs': sni_certs}

    def _process_secret(self, listener, secret_ref, amphora=None, obj_id=None):
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
        md5sum = md5(secret, usedforsecurity=False).hexdigest()  # nosec
        id = hashlib.sha1(secret).hexdigest()  # nosec
        name = '{id}.pem'.format(id=id)

        if amphora and obj_id:
            self._upload_cert(
                amphora, obj_id, pem=secret, md5sum=md5sum, name=name)
        return name

    def _process_listener_pool_certs(self, listener, amphora, obj_id):
        #     {'POOL-ID': {
        #         'client_cert': client_full_filename,
        #         'ca_cert': ca_cert_full_filename,
        #         'crl': crl_full_filename}}
        pool_certs_dict = {}
        for pool in listener.pools:
            if pool.id not in pool_certs_dict:
                pool_certs_dict[pool.id] = self._process_pool_certs(
                    listener, pool, amphora, obj_id)
        for l7policy in listener.l7policies:
            if (l7policy.redirect_pool and
                    l7policy.redirect_pool.id not in pool_certs_dict):
                pool_certs_dict[l7policy.redirect_pool.id] = (
                    self._process_pool_certs(listener, l7policy.redirect_pool,
                                             amphora, obj_id))
        return pool_certs_dict

    def _process_pool_certs(self, listener, pool, amphora, obj_id):
        pool_cert_dict = {}

        # Handle the client cert(s) and key
        if pool.tls_certificate_id:
            data = cert_parser.load_certificates_data(self.cert_manager, pool)
            tls_cert = data['tls_cert']
            pem = cert_parser.build_pem(tls_cert)
            try:
                pem = pem.encode('utf-8')
            except AttributeError:
                pass
            md5sum = md5(pem, usedforsecurity=False).hexdigest()  # nosec
            name = '{id}.pem'.format(id=tls_cert.id)
            if amphora and obj_id:
                self._upload_cert(amphora, obj_id, pem=pem,
                                  md5sum=md5sum, name=name)
            pool_cert_dict['client_cert'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, obj_id, name)
        if pool.ca_tls_certificate_id:
            name = self._process_secret(listener, pool.ca_tls_certificate_id,
                                        amphora, obj_id)
            pool_cert_dict['ca_cert'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, obj_id, name)
        if pool.crl_container_id:
            name = self._process_secret(listener, pool.crl_container_id,
                                        amphora, obj_id)
            pool_cert_dict['crl'] = os.path.join(
                CONF.haproxy_amphora.base_cert_dir, obj_id, name)

        return pool_cert_dict

    def _upload_cert(self, amp, listener_id, pem, md5sum, name):
        try:
            if self.clients[amp.api_version].get_cert_md5sum(
                    amp, listener_id, name, ignore=(404,)) == md5sum:
                return
        except exc.NotFound:
            pass

        self.clients[amp.api_version].upload_cert_pem(
            amp, listener_id, name, pem)

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
            self._populate_amphora_api_version(amphora)
            self.clients[amphora.api_version].update_agent_config(
                amphora, agent_config, timeout_dict=timeout_dict)
        except exc.NotFound as e:
            LOG.debug('Amphora %s does not support the update_agent_config '
                      'API.', amphora.id)
            raise driver_except.AmpDriverNotImplementedError() from e

    def get_interface_from_ip(self, amphora, ip_address, timeout_dict=None):
        """Get the interface name for an IP address.

        :param amphora: The amphora to query.
        :type amphora: octavia.db.models.Amphora
        :param ip_address: The IP address to lookup. (IPv4 or IPv6)
        :type ip_address: string
        :param timeout_dict: Dictionary of timeout values for calls to the
                             amphora. May contain: req_conn_timeout,
                             req_read_timeout, conn_max_retries,
                             conn_retry_interval
        :type timeout_dict: dict
        :returns: None if not found, the interface name string if found.
        """
        try:
            self._populate_amphora_api_version(amphora, timeout_dict)
            response_json = self.clients[amphora.api_version].get_interface(
                amphora, ip_address, timeout_dict, log_error=False)
            return response_json.get('interface', None)
        except (exc.NotFound, driver_except.TimeOutException):
            return None


# Check a custom hostname
class CustomHostNameCheckingAdapter(requests.adapters.HTTPAdapter):
    def cert_verify(self, conn, url, verify, cert):
        conn.assert_hostname = self.uuid
        return super().cert_verify(conn, url, verify, cert)

    def init_poolmanager(self, *pool_args, **pool_kwargs):
        proto = CONF.amphora_agent.agent_tls_protocol.replace('.', '_')
        pool_kwargs['ssl_version'] = getattr(ssl, "PROTOCOL_%s" % proto)
        return super().init_poolmanager(*pool_args, **pool_kwargs)


class AmphoraAPIClientBase(object):
    def __init__(self):
        super().__init__()

        self.get = functools.partial(self.request, 'get')
        self.post = functools.partial(self.request, 'post')
        self.put = functools.partial(self.request, 'put')
        self.delete = functools.partial(self.request, 'delete')
        self.head = functools.partial(self.request, 'head')

        self.session = requests.Session()
        self.session.cert = CONF.haproxy_amphora.client_cert
        self.ssl_adapter = CustomHostNameCheckingAdapter()
        self.session.mount('https://', self.ssl_adapter)

    def _base_url(self, ip, api_version=None):
        if utils.is_ipv6_lla(ip):
            ip = '[{ip}%{interface}]'.format(
                ip=ip,
                interface=CONF.haproxy_amphora.lb_network_interface)
        elif utils.is_ipv6(ip):
            ip = '[{ip}]'.format(ip=ip)
        if api_version:
            return "https://{ip}:{port}/{version}/".format(
                ip=ip,
                port=CONF.haproxy_amphora.bind_port,
                version=api_version)
        return "https://{ip}:{port}/".format(
            ip=ip,
            port=CONF.haproxy_amphora.bind_port)

    def request(self, method: str, amp: db_models.Amphora, path: str = '/',
                timeout_dict: Optional[dict] = None,
                retry_404: bool = True, raise_retry_exception: bool = False,
                **kwargs):
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
        _url = self._base_url(amp.lb_network_ip, amp.api_version) + path
        LOG.debug("request url %s", _url)
        reqargs = {
            'verify': CONF.haproxy_amphora.server_ca,
            'url': _url,
            'timeout': (req_conn_timeout, req_read_timeout), }
        reqargs.update(kwargs)
        headers = reqargs.setdefault('headers', {})

        headers['User-Agent'] = (
            f"Octavia HaProxy Rest Client/{amp.api_version} "
            f"(https://wiki.openstack.org/wiki/Octavia)")
        self.ssl_adapter.uuid = amp.id
        exception = None
        # Keep retrying
        for dummy in range(conn_max_retries):
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
                    if not retry_404:
                        raise exc.NotFound()
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
                if raise_retry_exception:
                    # For taskflow persistence cause attribute should
                    # be serializable to JSON. Pass None, as cause exception
                    # is described in the expection message.
                    raise driver_except.AmpConnectionRetry(
                        exception=str(e)) from None
        LOG.error("Connection retries (currently set to %(max_retries)s) "
                  "exhausted.  The amphora is unavailable. Reason: "
                  "%(exception)s",
                  {'max_retries': conn_max_retries,
                   'exception': exception})
        raise driver_except.TimeOutException()

    def get_api_version(self, amp, timeout_dict=None,
                        raise_retry_exception=False):
        amp.api_version = None
        r = self.get(amp, retry_404=False, timeout_dict=timeout_dict,
                     raise_retry_exception=raise_retry_exception)
        # Handle 404 special as we don't want to log an ERROR on 404
        exc.check_exception(r, (404,))
        if r.status_code == 404:
            raise exc.NotFound()
        return r.json()


class AmphoraAPIClient1_0(AmphoraAPIClientBase):
    def __init__(self):
        super().__init__()

        self.start_listener = functools.partial(self._action,
                                                consts.AMP_ACTION_START)
        self.reload_listener = functools.partial(self._action,
                                                 consts.AMP_ACTION_RELOAD)

        self.start_vrrp = functools.partial(self._vrrp_action,
                                            consts.AMP_ACTION_START)
        self.stop_vrrp = functools.partial(self._vrrp_action,
                                           consts.AMP_ACTION_STOP)
        self.reload_vrrp = functools.partial(self._vrrp_action,
                                             consts.AMP_ACTION_RELOAD)

    def upload_config(self, amp, loadbalancer_id, config, timeout_dict=None):
        r = self.put(
            amp,
            'loadbalancer/{amphora_id}/{loadbalancer_id}/haproxy'.format(
                amphora_id=amp.id, loadbalancer_id=loadbalancer_id),
            timeout_dict, data=config)
        return exc.check_exception(r)

    def get_listener_status(self, amp, listener_id):
        r = self.get(
            amp,
            'listeners/{listener_id}'.format(listener_id=listener_id))
        if exc.check_exception(r):
            return r.json()
        return None

    def _action(self, action, amp, object_id, timeout_dict=None):
        r = self.put(
            amp, 'loadbalancer/{object_id}/{action}'.format(
                object_id=object_id, action=action),
            timeout_dict=timeout_dict)
        return exc.check_exception(r)

    def upload_cert_pem(self, amp, loadbalancer_id, pem_filename, pem_file):
        r = self.put(
            amp,
            'loadbalancer/{loadbalancer_id}/certificates/{filename}'.format(
                loadbalancer_id=loadbalancer_id, filename=pem_filename),
            data=pem_file)
        return exc.check_exception(r)

    def get_cert_md5sum(self, amp, loadbalancer_id, pem_filename,
                        ignore=tuple()):
        r = self.get(
            amp,
            'loadbalancer/{loadbalancer_id}/certificates/{filename}'.format(
                loadbalancer_id=loadbalancer_id, filename=pem_filename))
        if exc.check_exception(r, ignore):
            return r.json().get("md5sum")
        return None

    def delete_cert_pem(self, amp, loadbalancer_id, pem_filename):
        r = self.delete(
            amp,
            'loadbalancer/{loadbalancer_id}/certificates/{filename}'.format(
                loadbalancer_id=loadbalancer_id, filename=pem_filename))
        return exc.check_exception(r, (404,))

    def update_cert_for_rotation(self, amp, pem_file):
        r = self.put(amp, 'certificate', data=pem_file)
        return exc.check_exception(r)

    def delete_listener(self, amp, object_id):
        r = self.delete(
            amp, 'listeners/{object_id}'.format(object_id=object_id))
        return exc.check_exception(r, (404,))

    def get_info(self, amp, raise_retry_exception=False,
                 timeout_dict=None):
        r = self.get(amp, "info", raise_retry_exception=raise_retry_exception,
                     timeout_dict=timeout_dict)
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

    def _vrrp_action(self, action, amp, timeout_dict=None):
        r = self.put(amp, 'vrrp/{action}'.format(action=action),
                     timeout_dict=timeout_dict)
        return exc.check_exception(r)

    def get_interface(self, amp, ip_addr, timeout_dict=None, log_error=True):
        r = self.get(amp, 'interface/{ip_addr}'.format(ip_addr=ip_addr),
                     timeout_dict=timeout_dict)
        return exc.check_exception(r, log_error=log_error).json()

    # The function is used for all LVS-supported protocol listener (UDP, SCTP)
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
