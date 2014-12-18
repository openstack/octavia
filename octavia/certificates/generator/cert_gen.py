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
Certificate Generator API
"""
import abc

import six


@six.add_metaclass(abc.ABCMeta)
class CertGenerator(object):
    """Base Cert Generator Interface

    A Certificate Generator is responsible for generating private keys,
    generating CSRs, and signing TLS certificates.
    """

    @abc.abstractmethod
    def sign_cert(self, csr, validity):
        """Generates a signed certificate from the provided CSR

        This call is designed to block until a signed certificate can be
        returned.

        :param csr: A Certificate Signing Request
        :param validity: Valid for <validity> seconds from the current time

        :return: PEM Encoded Signed certificate
        :raises Exception: If certificate signing fails
        """
        pass

    @abc.abstractmethod
    def generate_cert_key_pair(self, cn, validity, bit_length, passphrase):
        """Generates a private key and certificate pair

        :param cn: Common name to use for the Certificate
        :param validity: Validity period for the Certificate
        :param bit_length: Private key bit length
        :param passphrase: Passphrase to use for encrypting the private key

        :return: octavia.certificates.common.Cert representation of the
                 certificate data
        :raises Exception: If generation fails
        """
        pass
