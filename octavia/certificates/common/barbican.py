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
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.certificates.common import cert
from octavia.common import keystone
from octavia.i18n import _LE


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class BarbicanCert(cert.Cert):
    """Representation of a Cert based on the Barbican CertificateContainer."""
    def __init__(self, cert_container):
        if not isinstance(cert_container,
                          barbican_client.containers.CertificateContainer):
            raise TypeError(_LE(
                "Retrieved Barbican Container is not of the correct type "
                "(certificate)."))
        self._cert_container = cert_container

    def get_certificate(self):
        if self._cert_container.certificate:
            return self._cert_container.certificate.payload

    def get_intermediates(self):
        if self._cert_container.intermediates:
            return self._cert_container.intermediates.payload

    def get_private_key(self):
        if self._cert_container.private_key:
            return self._cert_container.private_key.payload

    def get_private_key_passphrase(self):
        if self._cert_container.private_key_passphrase:
            return self._cert_container.private_key_passphrase.payload


class BarbicanAuth(object):
    _barbican_client = None

    @classmethod
    def get_barbican_client(cls):
        """Creates a Barbican client object.

        :return: a Barbican Client object
        :raises Exception: if the client cannot be created
        """
        if not cls._barbican_client:
            try:
                cls._barbican_client = barbican_client.Client(
                    session=keystone.get_session()
                )
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    LOG.error(_LE(
                        "Error creating Barbican client: %s"), e)
        return cls._barbican_client
