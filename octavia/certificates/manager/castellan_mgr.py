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
from OpenSSL import crypto
from oslo_log import log as logging

from octavia.certificates.common import pkcs12
from octavia.certificates.manager import cert_mgr
from octavia.common import exceptions

LOG = logging.getLogger(__name__)


class CastellanCertManager(cert_mgr.CertManager):
    """Certificate Manager for the Castellan library."""

    def __init__(self):
        super(CastellanCertManager, self).__init__()
        self.manager = key_manager.API()

    def store_cert(self, context, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name="PKCS12 Certificate Bundle"):
        p12 = crypto.PKCS12()
        p12.set_certificate(certificate)
        p12.set_privatekey(private_key)
        if intermediates:
            p12.set_ca_certificates(intermediates)
        if private_key_passphrase:
            raise exceptions.CertificateStorageException(
                "Passphrases protected PKCS12 certificates are not supported.")

        p12_data = opaque_data.OpaqueData(p12.export(), name=name)
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
