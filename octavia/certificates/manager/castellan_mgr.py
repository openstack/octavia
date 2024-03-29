# Copyright (c) 2017 GoDaddy
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
Cert manager implementation for Castellan
"""
from castellan.common.objects import opaque_data
from castellan import key_manager
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12 as c_pkcs12
from oslo_config import cfg
from oslo_log import log as logging

from octavia.certificates.common import pkcs12
from octavia.certificates.manager import cert_mgr
from octavia.common import exceptions

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


class CastellanCertManager(cert_mgr.CertManager):
    """Certificate Manager for the Castellan library."""

    def __init__(self):
        super().__init__()
        self.manager = key_manager.API(CONF)

    def store_cert(self, context, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name="PKCS12 Certificate Bundle"):
        if private_key_passphrase:
            raise exceptions.CertificateStorageException(
                "Passphrases protected PKCS12 certificates are not supported.")

        p12_data = opaque_data.OpaqueData(
            c_pkcs12.serialize_key_and_certificates(
                name=None,
                key=private_key,
                cert=certificate,
                cas=intermediates,
                encryption_algorithm=serialization.NoEncryption()
            ),
            name=name
        )
        self.manager.store(context, p12_data)

    def get_cert(self, context, cert_ref, resource_ref=None, check_only=False,
                 service_name=None):
        certbag = self.manager.get(context, cert_ref)
        certbag_data = certbag.get_encoded()
        cert = pkcs12.PKCS12Cert(certbag_data)
        return cert

    def delete_cert(self, context, cert_ref, resource_ref, service_name=None):
        # Delete is not a great name for this -- we don't delete anything
        # in reality, we just do cleanup here. For castellan, none is required
        pass

    def set_acls(self, context, cert_ref):
        # We don't manage ACL based access for things retrieved via Castellan
        # because we assume we have elevated access to the secret store.
        pass

    def unset_acls(self, context, cert_ref):
        # We don't manage ACL based access for things retrieved via Castellan
        # because we assume we have elevated access to the secret store.
        pass

    def get_secret(self, context, secret_ref):
        try:
            certbag = self.manager.get(context, secret_ref)
            certbag_data = certbag.get_encoded()
        except Exception as e:
            LOG.error("Failed to access secret for %s due to: %s.",
                      secret_ref, str(e))
            raise exceptions.CertificateRetrievalException(ref=secret_ref)
        return certbag_data
