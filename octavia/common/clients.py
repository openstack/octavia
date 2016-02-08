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

from neutronclient.neutron import client as neutron_client
from novaclient import client as nova_client
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.common import keystone
from octavia.i18n import _LE

LOG = logging.getLogger(__name__)
NEUTRON_VERSION = '2.0'
NOVA_VERSION = '2'


class NovaAuth(object):
    nova_client = None

    @classmethod
    def get_nova_client(cls, region, service_name=None, endpoint=None,
                        endpoint_type='publicURL'):
        """Create nova client object.

        :param region: The region of the service
        :param service_name: The name of the nova service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The type of the endpoint
        :return: a Nova Client object.
        :raises Exception: if the client cannot be created
        """
        if not cls.nova_client:
            kwargs = {'region_name': region,
                      'session': keystone.get_session(),
                      'endpoint_type': endpoint_type}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint_override'] = endpoint
            try:
                cls.nova_client = nova_client.Client(
                    NOVA_VERSION, **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception(_LE("Error creating Nova client."))
        return cls.nova_client


class NeutronAuth(object):
    neutron_client = None

    @classmethod
    def get_neutron_client(cls, region, service_name=None, endpoint=None,
                           endpoint_type='publicURL'):
        """Create neutron client object.

        :param region: The region of the service
        :param service_name: The name of the neutron service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The endpoint_type of the service
        :return: a Neutron Client object.
        :raises Exception: if the client cannot be created
        """
        if not cls.neutron_client:
            kwargs = {'region_name': region,
                      'session': keystone.get_session(),
                      'endpoint_type': endpoint_type}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint_override'] = endpoint
            try:
                cls.neutron_client = neutron_client.Client(
                    NEUTRON_VERSION, **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception(_LE("Error creating Neutron client."))
        return cls.neutron_client
