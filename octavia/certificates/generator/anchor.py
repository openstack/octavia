# Copyright (c) 2015 Hewlett Packard Enterprise Development Company LP
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

from oslo_config import cfg
from oslo_log import log as logging
import requests

from octavia.certificates.generator import local
from octavia.common import exceptions

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class AnchorException(exceptions.CertificateGenerationException):
    pass


class AnchorCertGenerator(local.LocalCertGenerator):
    """Cert Generator Interface that signs certs with Anchor."""

    @classmethod
    def sign_cert(cls, csr, validity=None, **kwargs):
        """Signs a certificate using Anchor based on the specified CSR

        :param csr: A Certificate Signing Request
        :param validity: Will be ignored for now
        :param kwargs: Will be ignored for now

        :return: Signed certificate
        :raises Exception: if certificate signing fails
        """
        LOG.debug("Signing a certificate request using Anchor")

        try:
            LOG.debug('Certificate: %s', csr)
            r = requests.post(CONF.anchor.url, data={
                'user': CONF.anchor.username,
                'secret': CONF.anchor.password,
                'encoding': 'pem',
                'csr': csr})

            if r.status_code != 200:
                LOG.debug('Anchor returned: %s', r.content)
                raise AnchorException(_("Anchor returned Status Code : "
                                        "{0}").format(str(r.status_code)))

            return r.content

        except Exception as e:
            LOG.error("Unable to sign certificate.")
            raise exceptions.CertificateGenerationException(msg=e)
