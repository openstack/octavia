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
Cert generator implementation for Barbican
"""
import random
import time

from oslo_log import log as logging

from octavia.certificates.common import barbican as barbican_common
from octavia.certificates.generator import cert_gen


LOG = logging.getLogger(__name__)

MAX_ATTEMPTS = 10


class BarbicanCertGenerator(cert_gen.CertGenerator):
    """Certificate Generator that wraps the Barbican client API."""

    @classmethod
    def sign_cert(cls, csr, validity):
        """Signs a certificate using our private CA based on the specified CSR.

        :param csr: A Certificate Signing Request
        :param validity: Valid for <validity> seconds from the current time

        :return: Signed certificate
        :raises Exception: if certificate signing fails
        """
        raise NotImplementedError("Barbican does not yet support signing.")

    @classmethod
    def _generate_private_key(cls, bit_length=2048, passphrase=None,
                              create_only=False):
        """Generates a private key

        :param bit_length: Private key bit length (default 2048)
        :param passphrase: Passphrase to use for encrypting the private key

        :return: PEM encoded private key
        :raises Exception: If private key generation fails
        """
        connection = barbican_common.BarbicanAuth.get_barbican_client()
        order = connection.orders.create_asymmetric(
            bit_length=bit_length,
            algorithm='rsa',
            pass_phrase=passphrase,
            payload_content_type='application/octet-stream'
        )
        order.submit()

        attempts = 0
        while (order.container_ref is None and order.status != 'ERROR'
               and attempts < MAX_ATTEMPTS):
            backoff = float(1 << attempts) + random.random() * attempts
            time.sleep(backoff)
            order = connection.orders.get(order.order_ref)
            attempts += 1

        if order.status != 'ACTIVE':
            raise Exception("Barbican failed to generate a private key.")

        container = connection.containers.get(order.container_ref)
        secret = container.private_key

        if not create_only:
            try:
                pk = secret.payload
            except ValueError:
                secret = connection.secrets.get(
                    secret_ref=secret.secret_ref,
                    payload_content_type='application/octet-stream'
                )
                pk = secret.payload
            return pk

        return secret.secret_ref

    @classmethod
    def _sign_cert_from_stored_key(cls, cn, pk_ref, validity):
        raise NotImplementedError("Barbican does not yet support signing.")

    @classmethod
    def generate_cert_key_pair(cls, cn, validity, bit_length=2048,
                               passphrase=None):
        # This code will essentially work once Barbican enables CertOrders
        # pk = cls._generate_private_key(
        #     bit_length=bit_length,
        #     passphrase=passphrase,
        #     create_only=True
        # )
        # cert_container = cls._sign_cert_from_stored_key(cn=cn, pk_ref=pk,
        #                                                 validity=validity)
        # return barbican_common.BarbicanCert(cert_container)
        raise NotImplementedError("Barbican does not yet support signing.")
