# Copyright (c) 2014 Rackspace US, Inc
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

"""
Common classes for Barbican certificate handling
"""

from barbicanclient import client as barbican_client
from keystoneclient.auth.identity import v3 as keystone_client
from keystoneclient import session
from oslo.config import cfg

from octavia.certificates.common import cert
from octavia.openstack.common import excutils
from octavia.openstack.common import gettextutils
from octavia.openstack.common import log as logging


LOG = logging.getLogger(__name__)

CONF = cfg.CONF
CONF.import_group('keystone_authtoken', 'octavia.common.config')


class BarbicanCert(cert.Cert):
    """Representation of a Cert based on the Barbican CertificateContainer."""
    def __init__(self, cert_container):
        if not isinstance(cert_container,
                          barbican_client.containers.CertificateContainer):
            raise TypeError(gettextutils._LE(
                "Retrieved Barbican Container is not of the correct type "
                "(certificate)."))
        self._cert_container = cert_container

    def get_certificate(self):
        return self._cert_container.certificate.payload

    def get_intermediates(self):
        return self._cert_container.intermediates.payload

    def get_private_key(self):
        return self._cert_container.private_key.payload

    def get_private_key_passphrase(self):
        return self._cert_container.private_key_passphrase.payload


class BarbicanKeystoneAuth(object):
    _keystone_session = None
    _barbican_client = None

    @classmethod
    def _get_keystone_session(cls):
        """Initializes a Keystone session.

        :return: a Keystone Session object
        :raises Exception: if the session cannot be established
        """
        if not cls._keystone_session:
            try:
                kc = keystone_client.Password(
                    auth_url=CONF.keystone_authtoken.auth_uri,
                    username=CONF.keystone_authtoken.admin_user,
                    password=CONF.keystone_authtoken.admin_password,
                    project_id=CONF.keystone_authtoken.admin_project_id
                )
                cls._keystone_session = session.Session(auth=kc)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error(gettextutils._LE(
                        "Error creating Keystone session: %s"), e)
        return cls._keystone_session

    @classmethod
    def get_barbican_client(cls):
        """Creates a Barbican client object.

        :return: a Barbican Client object
        :raises Exception: if the client cannot be created
        """
        if not cls._barbican_client:
            try:
                cls._barbican_client = barbican_client.Client(
                    session=cls._get_keystone_session()
                )
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error(gettextutils._LE(
                        "Error creating Barbican client: %s"), e)
        return cls._barbican_client
