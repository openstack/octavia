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

from cinderclient import client as cinder_client
from glanceclient import client as glance_client
from neutronclient.neutron import client as neutron_client
from novaclient import api_versions
from novaclient import client as nova_client
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.common import keystone

LOG = logging.getLogger(__name__)
CONF = cfg.CONF

GLANCE_VERSION = '2'
NEUTRON_VERSION = '2.0'
NOVA_VERSION = '2.15'
CINDER_VERSION = '3'


class NovaAuth(object):
    nova_client = None

    @classmethod
    def get_nova_client(cls, region, service_name=None, endpoint=None,
                        endpoint_type='publicURL', insecure=False,
                        cacert=None):
        """Create nova client object.

        :param region: The region of the service
        :param service_name: The name of the nova service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The type of the endpoint
        :param insecure: Turn off certificate validation
        :param cacert: CA Cert file path
        :return: a Nova Client object.
        :raises Exception: if the client cannot be created
        """
        ksession = keystone.KeystoneSession()
        if not cls.nova_client:
            kwargs = {'region_name': region,
                      'session': ksession.get_session(),
                      'endpoint_type': endpoint_type,
                      'insecure': insecure}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint_override'] = endpoint
            if cacert:
                kwargs['cacert'] = cacert
            try:
                cls.nova_client = nova_client.Client(
                    version=api_versions.APIVersion(NOVA_VERSION), **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Error creating Nova client.")
        return cls.nova_client


class NeutronAuth(object):
    neutron_client = None

    @classmethod
    def get_neutron_client(cls, region, service_name=None, endpoint=None,
                           endpoint_type='publicURL', insecure=False,
                           ca_cert=None):
        """Create neutron client object.

        :param region: The region of the service
        :param service_name: The name of the neutron service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The endpoint_type of the service
        :param insecure: Turn off certificate validation
        :param ca_cert: CA Cert file path
        :return: a Neutron Client object.
        :raises Exception: if the client cannot be created
        """
        ksession = keystone.KeystoneSession()
        if not cls.neutron_client:
            kwargs = {'region_name': region,
                      'session': ksession.get_session(),
                      'endpoint_type': endpoint_type,
                      'insecure': insecure}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint_override'] = endpoint
            if ca_cert:
                kwargs['ca_cert'] = ca_cert
            try:
                cls.neutron_client = neutron_client.Client(
                    NEUTRON_VERSION, **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Error creating Neutron client.")
        return cls.neutron_client

    @classmethod
    def get_user_neutron_client(cls, context):
        """Get neutron client for request user.

        It's possible that the token in the context is a trust scoped
        which can't be used to initialize a keystone session.

        We directly use the token and endpoint_url to initialize neutron
        client.
        """
        neutron_endpoint = CONF.neutron.endpoint
        if not neutron_endpoint:
            session = keystone.KeystoneSession().get_session()
            endpoint_data = session.get_endpoint_data(
                service_type='network', interface=CONF.neutron.endpoint_type,
                region_name=CONF.neutron.region_name)
            neutron_endpoint = endpoint_data.catalog_url

        kwargs = {
            'token': context.auth_token,
            'endpoint_url': neutron_endpoint,
            'insecure': CONF.neutron.insecure,
            'ca_cert': CONF.neutron.ca_certificates_file
        }

        return neutron_client.Client(NEUTRON_VERSION, **kwargs)


class GlanceAuth(object):
    glance_client = None

    @classmethod
    def get_glance_client(cls, region, service_name=None, endpoint=None,
                          endpoint_type='publicURL', insecure=False,
                          cacert=None):
        """Create glance client object.

        :param region: The region of the service
        :param service_name: The name of the glance service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The endpoint_type of the service
        :param insecure: Turn off certificate validation
        :param cacert: CA Cert file path
        :return: a Glance Client object.
        :raises Exception: if the client cannot be created
        """
        ksession = keystone.KeystoneSession()
        if not cls.glance_client:
            kwargs = {'region_name': region,
                      'session': ksession.get_session(),
                      'interface': endpoint_type}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint'] = endpoint
                if endpoint.startswith("https"):
                    kwargs['insecure'] = insecure
                    kwargs['cacert'] = cacert
            try:
                cls.glance_client = glance_client.Client(
                    GLANCE_VERSION, **kwargs)
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Error creating Glance client.")
        return cls.glance_client


class CinderAuth(object):
    cinder_client = None

    @classmethod
    def get_cinder_client(cls, region, service_name=None, endpoint=None,
                          endpoint_type='publicURL', insecure=False,
                          cacert=None):
        """Create cinder client object.

        :param region: The region of the service
        :param service_name: The name of the cinder service in the catalog
        :param endpoint: The endpoint of the service
        :param endpoint_type: The endpoint type of the service
        :param insecure: Turn off certificate validation
        :param cacert: CA Cert file path
        :return: a Cinder Client object
        :raise Exception: if the client cannot be created
        """
        ksession = keystone.KeystoneSession()
        if not cls.cinder_client:
            kwargs = {'region_name': region,
                      'session': ksession.get_session(),
                      'interface': endpoint_type}
            if service_name:
                kwargs['service_name'] = service_name
            if endpoint:
                kwargs['endpoint'] = endpoint
                if endpoint.startswith("https"):
                    kwargs['insecure'] = insecure
                    kwargs['cacert'] = cacert
            try:
                cls.cinder_client = cinder_client.Client(
                    CINDER_VERSION, **kwargs
                )
            except Exception:
                with excutils.save_and_reraise_exception():
                    LOG.exception("Error creating Cinder client.")
        return cls.cinder_client
