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
Common classes for pkcs12 based certificate handling
"""

from cryptography.hazmat.primitives import serialization
from OpenSSL import crypto

from octavia.certificates.common import cert
from octavia.common import exceptions


class PKCS12Cert(cert.Cert):
    """Representation of a Cert for local storage."""
    def __init__(self, certbag):
        try:
            p12 = crypto.load_pkcs12(certbag)
        except crypto.Error as e:
            raise exceptions.UnreadablePKCS12(error=str(e))
        self.certificate = p12.get_certificate()
        self.intermediates = p12.get_ca_certificates()
        self.private_key = p12.get_privatekey()

    def get_certificate(self):
        return self.certificate.to_cryptography().public_bytes(
            encoding=serialization.Encoding.PEM).strip()

    def get_intermediates(self):
        if self.intermediates:
            int_data = [
                ic.to_cryptography().public_bytes(
                    encoding=serialization.Encoding.PEM).strip()
                for ic in self.intermediates
            ]
            return int_data
        return None

    def get_private_key(self):
        return self.private_key.to_cryptography_key().private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()).strip()

    def get_private_key_passphrase(self):
        return None
