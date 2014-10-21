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
from octavia.certificates.generator import cert_gen
from octavia.openstack.common import log as logging


LOG = logging.getLogger(__name__)


class BarbicanCertGenerator(cert_gen.CertGenerator):
    """Certificate Generator that wraps the Barbican client API."""

    @staticmethod
    def sign_cert(csr, validity):
        """Signs a certificate using our private CA based on the specified CSR.

        :param csr: A Certificate Signing Request
        :param validity: Valid for <validity> seconds from the current time

        :return: Signed certificate
        :raises Exception: if certificate signing fails
        """
        raise NotImplementedError("Barbican does not yet support signing.")
