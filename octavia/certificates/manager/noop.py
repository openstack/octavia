# Copyright (c) 2023 Red Hat
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
import uuid

from oslo_log import log as logging

from octavia.certificates.common import cert
from octavia.certificates.common import local
from octavia.certificates.manager import cert_mgr
from octavia.common.tls_utils import cert_parser
from octavia.tests.common import sample_certs

LOG = logging.getLogger(__name__)


class NoopCertManager(cert_mgr.CertManager):
    """Cert manager implementation for no-op operations

    """
    def __init__(self):
        super().__init__()
        self._local_cert = None

    @property
    def local_cert(self):
        if self._local_cert is None:
            self._local_cert = self.store_cert(
                None,
                sample_certs.X509_CERT,
                sample_certs.X509_CERT_KEY_ENCRYPTED,
                sample_certs.X509_IMDS,
                private_key_passphrase=sample_certs.X509_CERT_KEY_PASSPHRASE)
        return self._local_cert

    def store_cert(self, context, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, **kwargs) -> cert.Cert:
        """Stores (i.e., registers) a cert with the cert manager.

        This method stores the specified cert to the filesystem and returns
        a UUID that can be used to retrieve it.

        :param context: Ignored in this implementation
        :param certificate: PEM encoded TLS certificate
        :param private_key: private key for the supplied certificate
        :param intermediates: ordered and concatenated intermediate certs
        :param private_key_passphrase: optional passphrase for the supplied key

        :returns: the UUID of the stored cert
        :raises CertificateStorageException: if certificate storage fails
        """
        cert_ref = str(uuid.uuid4())
        if isinstance(certificate, bytes):
            certificate = certificate.decode('utf-8')
        if isinstance(private_key, bytes):
            private_key = private_key.decode('utf-8')

        LOG.debug('Driver %s no-op, store_cert certificate %s, cert_ref %s',
                  self.__class__.__name__, certificate, cert_ref)

        cert_data = {'certificate': certificate, 'private_key': private_key}
        if intermediates:
            if isinstance(intermediates, bytes):
                intermediates = intermediates.decode('utf-8')
            cert_data['intermediates'] = list(
                cert_parser.get_intermediates_pems(intermediates))
        if private_key_passphrase:
            if isinstance(private_key_passphrase, bytes):
                private_key_passphrase = private_key_passphrase.decode('utf-8')
            cert_data['private_key_passphrase'] = private_key_passphrase

        return local.LocalCert(**cert_data)

    def get_cert(self, context, cert_ref, check_only=True, **kwargs) -> (
            cert.Cert):
        LOG.debug('Driver %s no-op, get_cert with cert_ref %s',
                  self.__class__.__name__, cert_ref)
        return self.local_cert

    def delete_cert(self, context, cert_ref, resource_ref, service_name=None):
        LOG.debug('Driver %s no-op, delete_cert with cert_ref %s',
                  self.__class__.__name__, cert_ref)

    def set_acls(self, context, cert_ref):
        LOG.debug('Driver %s no-op, set_acls with cert_ref %s',
                  self.__class__.__name__, cert_ref)

    def unset_acls(self, context, cert_ref):
        LOG.debug('Driver %s no-op, unset_acls with cert_ref %s',
                  self.__class__.__name__, cert_ref)

    def get_secret(self, context, secret_ref) -> cert.Cert:
        LOG.debug('Driver %s no-op, get_secret with secret_ref %s',
                  self.__class__.__name__, secret_ref)
        return self.local_cert
