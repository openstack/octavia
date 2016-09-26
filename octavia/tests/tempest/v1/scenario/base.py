# Copyright 2016 Rackspace Inc.
# All Rights Reserved.
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

try:
    from http import cookiejar as cookielib
except ImportError:
    import cookielib
import shlex
import socket
import subprocess
import tempfile
import time

from oslo_log import log as logging
import six
from six.moves.urllib import error
from six.moves.urllib import request as urllib2
from tempest.common import credentials_factory
from tempest.common import waiters
from tempest import config
from tempest import exceptions
from tempest.lib.common.utils import test_utils
from tempest.lib import exceptions as lib_exc
from tempest.scenario import manager
from tempest import test


from octavia.i18n import _
from octavia.tests.tempest.v1.clients import health_monitors_client
from octavia.tests.tempest.v1.clients import listeners_client
from octavia.tests.tempest.v1.clients import load_balancers_client
from octavia.tests.tempest.v1.clients import members_client
from octavia.tests.tempest.v1.clients import pools_client

config = config.CONF

LOG = logging.getLogger(__name__)


class BaseTestCase(manager.NetworkScenarioTest):

    def setUp(self):
        super(BaseTestCase, self).setUp()
        self.servers_keypairs = {}
        self.servers = {}
        self.members = []
        self.floating_ips = {}
        self.servers_floating_ips = {}
        self.server_ips = {}
        self.port1 = 80
        self.port2 = 88
        self.num = 50
        self.server_ips = {}
        self.server_fixed_ips = {}

        self._create_security_group_for_test()
        self._set_net_and_subnet()

        mgr = self.get_client_manager()

        auth_provider = mgr.auth_provider
        region = config.network.region or config.identity.region
        self.client_args = [auth_provider, 'octavia', region]
        self.load_balancers_client = (
            load_balancers_client.LoadBalancersClient(*self.client_args))
        self.listeners_client = (
            listeners_client.ListenersClient(*self.client_args))
        self.pools_client = pools_client.PoolsClient(*self.client_args)
        self.members_client = members_client.MembersClient(
            *self.client_args)
        self.health_monitors_client = (
            health_monitors_client.HealthMonitorsClient(
                *self.client_args))

        # admin network client needed for assigning octavia port to flip
        admin_manager = credentials_factory.AdminManager()
        admin_manager.auth_provider.fill_credentials()
        self.floating_ips_client_admin = admin_manager.floating_ips_client
        self.ports_client_admin = admin_manager.ports_client

    @classmethod
    def skip_checks(cls):
        super(BaseTestCase, cls).skip_checks()
        cfg = config.network
        if not test.is_extension_enabled('lbaasv2', 'network'):
            msg = 'LBaaS Extension is not enabled'
            raise cls.skipException(msg)
        if not (cfg.project_networks_reachable or cfg.public_network_id):
            msg = ('Either project_networks_reachable must be "true", or '
                   'public_network_id must be defined.')
            raise cls.skipException(msg)

    def _set_net_and_subnet(self):
        """Set Network and Subnet

        Query and set appropriate network and subnet attributes to be used
        for the test. Existing tenant networks are used if they are found.
        The configured private network and associated subnet is used as a
        fallback in absence of tenant networking.
        """
        try:
            tenant_net = self._list_networks(tenant_id=self.tenant_id)[0]
        except IndexError:
            tenant_net = None

        if tenant_net:
            tenant_subnet = self._list_subnets(tenant_id=self.tenant_id)[0]
            self.subnet = tenant_subnet
            self.network = tenant_net
        else:
            self.network = self._get_network_by_name(
                config.compute.fixed_network_name)
            # We are assuming that the first subnet associated
            # with the fixed network is the one we want.  In the future, we
            # should instead pull a subnet id from config, which is set by
            # devstack/admin/etc.
            subnet = self._list_subnets(network_id=self.network['id'])[0]
            self.subnet = subnet

    def _create_security_group_for_test(self):
        self.security_group = self._create_security_group(
            tenant_id=self.tenant_id)
        self._create_security_group_rules_for_port(self.port1)
        self._create_security_group_rules_for_port(self.port2)

    def _create_security_group_rules_for_port(self, port):
        rule = {
            'direction': 'ingress',
            'protocol': 'tcp',
            'port_range_min': port,
            'port_range_max': port,
        }
        self._create_security_group_rule(
            secgroup=self.security_group,
            tenant_id=self.tenant_id,
            **rule)

    def _ipv6_subnet(self, address6_mode):
        router = self._get_router(tenant_id=self.tenant_id)
        self.network = self._create_network(tenant_id=self.tenant_id)
        self.subnet = self._create_subnet(network=self.network,
                                          namestart='sub6',
                                          ip_version=6,
                                          ipv6_ra_mode=address6_mode,
                                          ipv6_address_mode=address6_mode)
        self.subnet.add_to_router(router_id=router['id'])
        self.addCleanup(self.subnet.delete)

    def _create_server(self, name):
        keypair = self.create_keypair()
        security_groups = [{'name': self.security_group['name']}]
        create_kwargs = {
            'networks': [
                {'uuid': self.network['id']},
            ],
            'key_name': keypair['name'],
            'security_groups': security_groups,
        }
        net_name = self.network['name']
        server = self.create_server(name=name, **create_kwargs)
        waiters.wait_for_server_status(self.servers_client,
                                       server['id'], 'ACTIVE')
        server = self.servers_client.show_server(server['id'])
        server = server['server']
        self.servers_keypairs[server['id']] = keypair

        LOG.info(('servers_keypairs looks like this(format): {0}'.format(
            self.servers_keypairs)))

        if (config.network.public_network_id and not
                config.network.project_networks_reachable):
            public_network_id = config.network.public_network_id
            floating_ip = self._create_floating_ip(
                server, public_network_id)
            self.floating_ips[floating_ip['id']] = server
            self.server_ips[server['id']] = floating_ip['floating_ip_address']

        else:
            self.server_ips[server['id']] = (
                server['addresses'][net_name][0]['addr'])

        self.server_fixed_ips[server['id']] = (
            server['addresses'][net_name][0]['addr'])
        self.assertTrue(self.servers_keypairs)
        return server

    def _create_servers(self):
        for count in range(2):
            self.server = self._create_server(name=("server%s" % (count + 1)))
            if count == 0:
                self.servers['primary'] = self.server['id']
            else:
                self.servers['secondary'] = self.server['id']
        self.assertEqual(len(self.servers_keypairs), 2)

    def _stop_server(self):
        for name, value in six.iteritems(self.servers):
            if name == 'primary':
                LOG.info(('STOPPING SERVER: {0}'.format(name)))
                self.servers_client.stop_server(value)
                waiters.wait_for_server_status(self.servers_client,
                                               value, 'SHUTOFF')
        LOG.info(('STOPPING SERVER COMPLETED!'))

    def _start_server(self):
        for name, value in six.iteritems(self.servers):
            if name == 'primary':
                self.servers_client.start(value)
                waiters.wait_for_server_status(self.servers_client,
                                               value, 'ACTIVE')

    def _start_servers(self):
        """Start one or more backends

        1. SSH to the instance
        2. Start two http backends listening on ports 80 and 88 respectively
        """
        for server_id, ip in six.iteritems(self.server_ips):
            private_key = self.servers_keypairs[server_id]['private_key']
            server = self.servers_client.show_server(server_id)['server']
            server_name = server['name']
            username = config.validation.image_ssh_user
            ssh_client = self.get_remote_client(
                ip_address=ip,
                private_key=private_key)

            # Write a backend's response into a file
            resp = ('echo -ne "HTTP/1.1 200 OK\r\nContent-Length: 7\r\n'
                    'Set-Cookie:JSESSIONID=%(s_id)s\r\nConnection: close\r\n'
                    'Content-Type: text/html; '
                    'charset=UTF-8\r\n\r\n%(server)s"; cat >/dev/null')

            with tempfile.NamedTemporaryFile() as script:
                script.write(resp % {'s_id': server_name[-1],
                                     'server': server_name})
                script.flush()
                with tempfile.NamedTemporaryFile() as key:
                    key.write(private_key)
                    key.flush()
                    self.copy_file_to_host(script.name,
                                           "/tmp/script1",
                                           ip,
                                           username, key.name)

            # Start netcat
            start_server = ('while true; do '
                            'sudo nc -ll -p %(port)s -e sh /tmp/%(script)s; '
                            'done > /dev/null &')
            cmd = start_server % {'port': self.port1,
                                  'script': 'script1'}
            ssh_client.exec_command(cmd)

            if len(self.server_ips) == 1:
                with tempfile.NamedTemporaryFile() as script:
                    script.write(resp % {'s_id': 2,
                                         'server': 'server2'})
                    script.flush()
                    with tempfile.NamedTemporaryFile() as key:
                        key.write(private_key)
                        key.flush()
                        self.copy_file_to_host(script.name,
                                               "/tmp/script2", ip,
                                               username, key.name)
                cmd = start_server % {'port': self.port2,
                                      'script': 'script2'}
                ssh_client.exec_command(cmd)

    def _create_listener(self, load_balancer_id, default_pool_id=None):
        """Create a listener with HTTP protocol listening on port 80."""
        self.create_listener_kwargs = {'protocol': 'HTTP',
                                       'protocol_port': 80,
                                       'default_pool_id': default_pool_id}
        self.listener = self.listeners_client.create_listener(
            lb_id=load_balancer_id,
            **self.create_listener_kwargs)
        self.assertTrue(self.listener)
        self.addCleanup(self._cleanup_listener, load_balancer_id,
                        self.listener.get('id'))
        return self.listener

    def _create_health_monitor(self):
        """Create a HTTP health monitor."""
        self.hm = self.health_monitors_client.create_health_monitor(
            type='HTTP', delay=3, timeout=5,
            fall_threshold=5, rise_threshold=5,
            lb_id=self.load_balancer['id'],
            pool_id=self.pool['id'])
        self.assertTrue(self.hm)
        self.addCleanup(self._cleanup_health_monitor,
                        load_balancer_id=self.load_balancer['id'],
                        pool_id=self.pool['id'])
        self._wait_for_load_balancer_status(self.load_balancer['id'])

        # add clean up members prior to clean up of health monitor
        # see bug 1547609
        members = self.members_client.list_members(self.load_balancer['id'],
                                                   self.pool['id'])
        self.assertTrue(members)
        for member in members:
            self.addCleanup(self._cleanup_member,
                            load_balancer_id=self.load_balancer['id'],
                            pool_id=self.pool['id'],
                            member_id=member['id'])

    def _create_pool(self, load_balancer_id,
                     persistence_type=None, cookie_name=None):
        """Create a pool with ROUND_ROBIN algorithm."""
        create_pool_kwargs = {
            'lb_algorithm': 'ROUND_ROBIN',
            'protocol': 'HTTP'
        }
        if persistence_type:
            create_pool_kwargs.update(
                {'session_persistence': {'type': persistence_type}})
        if cookie_name:
            create_pool_kwargs.update(
                {'session_persistence': {'cookie_name': cookie_name}})
        self.pool = self.pools_client.create_pool(lb_id=load_balancer_id,
                                                  **create_pool_kwargs)
        self.assertTrue(self.pool)
        self.addCleanup(self._cleanup_pool, load_balancer_id,
                        self.pool['id'])
        return self.pool

    def _cleanup_load_balancer(self, load_balancer_id):
        test_utils.call_and_ignore_notfound_exc(
            self.load_balancers_client.delete_load_balancer, load_balancer_id)
        self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_listener(self, listener_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.listeners_client.delete_listener, load_balancer_id,
            listener_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_pool(self, pool_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.pools_client.delete_pool, load_balancer_id, pool_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _cleanup_health_monitor(self, hm_id, load_balancer_id=None):
        test_utils.call_and_ignore_notfound_exc(
            self.health_monitors_client.delete_health_monitor, hm_id)
        if load_balancer_id:
            self._wait_for_load_balancer_status(load_balancer_id, delete=True)

    def _create_members(self, load_balancer_id, pool_id, subnet_id=None):
        """Create one or more Members

        In case there is only one server, create both members with the same ip
        but with different ports to listen on.
        """
        for server_id, ip in six.iteritems(self.server_fixed_ips):
            if len(self.server_fixed_ips) == 1:
                create_member_kwargs = {
                    'ip_address': ip,
                    'protocol_port': self.port1,
                    'weight': 50,
                    'subnet_id': subnet_id
                }
                member1 = self.members_client.create_member(
                    lb_id=load_balancer_id,
                    pool_id=pool_id,
                    **create_member_kwargs)
                self._wait_for_load_balancer_status(load_balancer_id)
                create_member_kwargs = {
                    'ip_address': ip,
                    'protocol_port': self.port2,
                    'weight': 50,
                    'subnet_id': subnet_id
                }
                member2 = self.members_client.create_member(
                    lb_id=load_balancer_id,
                    pool_id=pool_id,
                    **create_member_kwargs)
                self._wait_for_load_balancer_status(load_balancer_id)
                self.members.extend([member1, member2])
            else:
                create_member_kwargs = {
                    'ip_address': ip,
                    'protocol_port': self.port1,
                    'weight': 50,
                    'subnet_id': subnet_id
                }
                member = self.members_client.create_member(
                    lb_id=load_balancer_id,
                    pool_id=pool_id,
                    **create_member_kwargs)
                self._wait_for_load_balancer_status(load_balancer_id)
                self.members.append(member)
        self.assertTrue(self.members)

    def _assign_floating_ip_to_lb_vip(self, lb):
        public_network_id = config.network.public_network_id

        LOG.info(('assign_floating_ip_to_lb_vip  lb: {0} type: {1}'.format(
            lb, type(lb))))
        port_id = lb['vip']['port_id']

        floating_ip = self._create_floating_ip(
            thing=lb,
            external_network_id=public_network_id,
            port_id=port_id,
            client=self.floating_ips_client_admin,
            tenant_id=self.floating_ips_client_admin.tenant_id)

        self.floating_ips.setdefault(lb['id'], [])
        self.floating_ips[lb['id']].append(floating_ip)
        # Check for floating ip status before you check load-balancer
        #
        # We need the admin client here and this method utilizes the non-admin
        # self.check_floating_ip_status(floating_ip, 'ACTIVE')
        self.check_flip_status(floating_ip, 'ACTIVE')

    def check_flip_status(self, floating_ip, status):
        """Verifies floatingip reaches the given status

        :param dict floating_ip: floating IP dict to check status
        :param status: target status
        :raises: AssertionError if status doesn't match
        """

        # TODO(ptoohill): Find a way to utilze the proper client method

        floatingip_id = floating_ip['id']

        def refresh():
            result = (self.floating_ips_client_admin.
                      show_floatingip(floatingip_id)['floatingip'])
            return status == result['status']

        test.call_until_true(refresh, 100, 1)

        floating_ip = self.floating_ips_client_admin.show_floatingip(
            floatingip_id)['floatingip']
        self.assertEqual(status, floating_ip['status'],
                         message="FloatingIP: {fp} is at status: {cst}. "
                                 "failed  to reach status: {st}"
                         .format(fp=floating_ip, cst=floating_ip['status'],
                                 st=status))
        LOG.info("FloatingIP: {fp} is at status: {st}"
                 .format(fp=floating_ip, st=status))

    def _create_load_balancer(self, ip_version=4, persistence_type=None):
        self.create_lb_kwargs = {'vip': {'subnet_id': self.subnet['id']}}
        self.load_balancer = self.load_balancers_client.create_load_balancer(
            **self.create_lb_kwargs)
        load_balancer_id = self.load_balancer['id']
        self.addCleanup(self._cleanup_load_balancer, load_balancer_id)
        LOG.info(('Waiting for lb status on create load balancer id: {0}'
                  .format(load_balancer_id)))
        self._wait_for_load_balancer_status(load_balancer_id=load_balancer_id,
                                            provisioning_status='ACTIVE',
                                            operating_status='ONLINE')

        self.pool = self._create_pool(load_balancer_id=load_balancer_id,
                                      persistence_type=persistence_type)
        self._wait_for_load_balancer_status(load_balancer_id)
        LOG.info(('Waiting for lb status on create pool id: {0}'.format(
            self.pool['id'])))

        self.listener = self._create_listener(
            load_balancer_id=load_balancer_id,
            default_pool_id=self.pool['id']
        )
        self._wait_for_load_balancer_status(load_balancer_id)
        LOG.info(('Waiting for lb status on create listener id: {0}'.format(
            self.listener['id'])))

        self._create_members(load_balancer_id=load_balancer_id,
                             pool_id=self.pool['id'],
                             subnet_id=self.subnet['id'])
        self.load_balancer = self._wait_for_load_balancer_status(
            load_balancer_id)
        LOG.info(('Waiting for lb status on create members...'))

        self.vip_ip = self.load_balancer['vip'].get('ip_address')

        # if the ipv4 is used for lb, then fetch the right values from
        # tempest.conf file
        if ip_version == 4:
            if (config.network.public_network_id and not
                    config.network.project_networks_reachable):
                load_balancer = self.load_balancer
                self._assign_floating_ip_to_lb_vip(load_balancer)
                self.vip_ip = self.floating_ips[
                    load_balancer['id']][0]['floating_ip_address']

        # Currently the ovs-agent is not enforcing security groups on the
        # vip port - see https://bugs.launchpad.net/neutron/+bug/1163569
        # However the linuxbridge-agent does, and it is necessary to add a
        # security group with a rule that allows tcp port 80 to the vip port.
        self.ports_client_admin.update_port(
            self.load_balancer['vip']['port_id'],
            security_groups=[self.security_group['id']])

    def _wait_for_load_balancer_status(self, load_balancer_id,
                                       provisioning_status='ACTIVE',
                                       operating_status='ONLINE',
                                       delete=False):
        interval_time = 1
        timeout = 600
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                lb = self.load_balancers_client.get_load_balancer(
                    load_balancer_id)
            except lib_exc.NotFound as e:
                if delete:
                    return
                else:
                    raise e

            LOG.info(('provisioning_status: {0}  operating_status: {1}'.format(
                lb.get('provisioning_status'),
                lb.get('operating_status'))))

            if delete and lb.get('provisioning_status') == 'DELETED':
                break
            elif (lb.get('provisioning_status') == provisioning_status and
                    lb.get('operating_status') == operating_status):
                break
            elif (lb.get('provisioning_status') == 'ERROR' or
                    lb.get('operating_status') == 'ERROR'):
                raise Exception(
                    _("Wait for load balancer for load balancer: {lb_id} "
                      "ran for {timeout} seconds and an ERROR was encountered "
                      "with provisioning status: {provisioning_status} and "
                      "operating status: {operating_status}").format(
                          timeout=timeout,
                          lb_id=lb.get('id'),
                          provisioning_status=provisioning_status,
                          operating_status=operating_status))
            time.sleep(interval_time)
        else:
            raise Exception(
                _("Wait for load balancer ran for {timeout} seconds and did "
                  "not observe {lb_id} reach {provisioning_status} "
                  "provisioning status and {operating_status} "
                  "operating status.").format(
                      timeout=timeout,
                      lb_id=lb.get('id'),
                      provisioning_status=provisioning_status,
                      operating_status=operating_status))
        return lb

    def _wait_for_pool_session_persistence(self, pool_id, sp_type=None):
        interval_time = 1
        timeout = 10
        end_time = time.time() + timeout
        while time.time() < end_time:
            pool = self.pools_client.get_pool(self.load_balancer['id'],
                                              pool_id)
            sp = pool.get('session_persistence', None)
            if (not (sp_type or sp) or
                    pool['session_persistence']['type'] == sp_type):
                return pool
            time.sleep(interval_time)
        raise Exception(
            _("Wait for pool ran for {timeout} seconds and did "
              "not observe {pool_id} update session persistence type "
              "to {type}.").format(
                  timeout=timeout,
                  pool_id=pool_id,
                  type=sp_type))

    def _check_load_balancing(self):
        """Check Load Balancing

        1. Send NUM requests on the floating ip associated with the VIP
        2. Check that the requests are shared between the two servers
        """
        LOG.info(_('Checking load balancing...'))
        self._check_connection(self.vip_ip)
        LOG.info(_('Connection to {vip} is valid').format(vip=self.vip_ip))
        counters = self._send_requests(self.vip_ip,
                                       ["server1", "server2"])
        for member, counter in six.iteritems(counters):
            self.assertGreater(counter, 0,
                               'Member %s never balanced' % member)
        LOG.info(_('Done checking load balancing...'))

    def _check_connection(self, check_ip, port=80):
        def try_connect(check_ip, port):
            try:
                LOG.info(('checking connection to ip: {0} port: {1}'.format(
                    check_ip, port)))
                resp = urllib2.urlopen("http://{0}:{1}/".format(check_ip,
                                                                port))
                if resp.getcode() == 200:
                    return True
                return False
            except IOError as e:
                LOG.info(('Got IOError in check connection: {0}'.format(e)))
                return False
            except error.HTTPError as e:
                LOG.info(('Got HTTPError in check connection: {0}'.format(e)))
                return False

        timeout = config.validation.ping_timeout
        start = time.time()
        while not try_connect(check_ip, port):
            if (time.time() - start) > timeout:
                message = "Timed out trying to connect to %s" % check_ip
                raise exceptions.TimeoutException(message)

    def _send_requests(self, vip_ip, servers):
        counters = dict.fromkeys(servers, 0)
        for i in range(self.num):
            try:
                server = urllib2.urlopen("http://{0}/".format(vip_ip),
                                         None, 2).read()
                counters[server] += 1
            # HTTP exception means fail of server, so don't increase counter
            # of success and continue connection tries
            except (error.HTTPError, error.URLError, socket.timeout) as e:
                LOG.info(('Got Error in sending request: {0}'.format(e)))
                continue
        # Check that we had at least sent more than 1 request
        counted = 0
        for server, counter in counters.items():
            counted += counter
        self.assertGreater(counted, 1)
        return counters

    def _traffic_validation_after_stopping_server(self):
        """Check that the requests are sent to the only ACTIVE server."""

        LOG.info(('Starting traffic_validation_after_stopping_server...'))
        counters = self._send_requests(self.vip_ip, ["server1", "server2"])
        LOG.info(('Counters is: {0}'.format(counters)))

        # Assert that no traffic is sent to server1.
        for member, counter in six.iteritems(counters):
            if member == 'server1':
                self.assertEqual(counter, 0,
                                 'Member %s is not balanced' % member)

    def _check_load_balancing_after_deleting_resources(self):
        """Check load balancer after deleting resources

        Check that the requests are not sent to any servers
        Assert that no traffic is sent to any servers
        """
        counters = self._send_requests(self.vip_ip, ["server1", "server2"])
        for member, counter in six.iteritems(counters):
            self.assertEqual(counter, 0, 'Member %s is balanced' % member)

    def _check_source_ip_persistence(self):
        """Check source ip session persistence.

        Verify that all requests from our ip are answered by the same server
        that handled it the first time.
        """
        # Check that backends are reachable
        self._check_connection(self.vip_ip)

        resp = []
        for count in range(10):
            resp.append(
                urllib2.urlopen("http://{0}/".format(self.vip_ip)).read())
        self.assertEqual(len(set(resp)), 1)

    def _update_pool_session_persistence(self, persistence_type=None,
                                         cookie_name=None):
        """Update a pool with new session persistence type and cookie name."""

        update_data = {}
        if persistence_type:
            update_data = {"session_persistence": {
                "type": persistence_type}}
        if cookie_name:
            update_data['session_persistence'].update(
                {"cookie_name": cookie_name})
        self.pools_client.update_pool(self.load_balancer['id'],
                                      self.pool['id'], **update_data)
        self.pool = self._wait_for_pool_session_persistence(
            self.load_balancer['id'],
            self.pool['id'],
            persistence_type)
        self._wait_for_load_balancer_status(self.load_balancer['id'])
        if persistence_type:
            self.assertEqual(persistence_type,
                             self.pool['session_persistence']['type'])
        if cookie_name:
            self.assertEqual(cookie_name,
                             self.pool['session_persistence']['cookie_name'])

    def _check_cookie_session_persistence(self):
        """Check cookie persistence types by injecting cookies in requests."""

        # Send first request and get cookie from the server's response
        cj = cookielib.CookieJar()
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj))
        opener.open("http://{0}/".format(self.vip_ip))
        resp = []
        # Send 10 subsequent requests with the cookie inserted in the headers.
        for count in range(10):
            request = urllib2.Request("http://{0}/".format(self.vip_ip))
            cj.add_cookie_header(request)
            response = urllib2.urlopen(request)
            resp.append(response.read())
        self.assertEqual(len(set(resp)), 1, message=resp)

    def _create_floating_ip(self, thing, external_network_id=None,
                            port_id=None, client=None, tenant_id=None):
        """Create a floating IP and associate to a resource/port on Neutron."""

        if not tenant_id:
            try:
                tenant_id = thing['tenant_id']
            except Exception:
                # Thing probably migrated to project_id, grab that...
                tenant_id = thing['project_id']

        if not external_network_id:
            external_network_id = config.network.public_network_id
        if not client:
            client = self.floating_ips_client
        if not port_id:
            port_id, ip4 = self._get_server_port_id_and_ip4(thing)
        else:
            ip4 = None
        result = client.create_floatingip(
            floating_network_id=external_network_id,
            port_id=port_id,
            tenant_id=tenant_id,
            fixed_ip_address=ip4
        )
        floating_ip = result['floatingip']
        self.addCleanup(test_utils.call_and_ignore_notfound_exc,
                        self.floating_ips_client.delete_floatingip,
                        floating_ip['id'])
        return floating_ip

    def copy_file_to_host(self, file_from, dest, host, username, pkey):
        dest = "%s@%s:%s" % (username, host, dest)
        cmd = ("scp -v -o UserKnownHostsFile=/dev/null "
               "-o StrictHostKeyChecking=no "
               "-i %(pkey)s %(file1)s %(dest)s" % {'pkey': pkey,
                                                   'file1': file_from,
                                                   'dest': dest})
        args = shlex.split(cmd.encode('utf-8'))
        subprocess_args = {'stdout': subprocess.PIPE,
                           'stderr': subprocess.STDOUT}
        proc = subprocess.Popen(args, **subprocess_args)
        stdout, stderr = proc.communicate()
        if proc.returncode != 0:
            LOG.error(("Command {0} returned with exit status {1},"
                      "output {2}, error {3}").format(cmd, proc.returncode,
                                                      stdout, stderr))
        return stdout
