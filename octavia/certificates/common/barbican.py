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

import abc

from barbicanclient.v1 import containers
from oslo_utils import encodeutils
import six

from octavia.certificates.common import cert
from octavia.common.tls_utils import cert_parser
from octavia.i18n import _


class BarbicanCert(cert.Cert):
    """Representation of a Cert based on the Barbican CertificateContainer."""
    def __init__(self, cert_container):
        if not isinstance(cert_container, containers.CertificateContainer):
            raise TypeError(_("Retrieved Barbican Container is not of the "
                              "correct type (certificate)."))
        self._cert_container = cert_container

    def get_certificate(self):
        if self._cert_container.certificate:
            return encodeutils.to_utf8(
                self._cert_container.certificate.payload)

    def get_intermediates(self):
        if self._cert_container.intermediates:
            intermediates = encodeutils.to_utf8(
                self._cert_container.intermediates.payload)
            return [imd for imd in cert_parser.get_intermediates_pems(
                intermediates)]

    def get_private_key(self):
        if self._cert_container.private_key:
            return encodeutils.to_utf8(
                self._cert_container.private_key.payload)

    def get_private_key_passphrase(self):
        if self._cert_container.private_key_passphrase:
            return encodeutils.to_utf8(
                self._cert_container.private_key_passphrase.payload)


@six.add_metaclass(abc.ABCMeta)
class BarbicanAuth(object):
    @abc.abstractmethod
    def get_barbican_client(self, project_id):
        """Creates a Barbican client object.

        :param project_id: Project ID that the request will be used for
        :return: a Barbican Client object
        :raises Exception: if the client cannot be created
        """
