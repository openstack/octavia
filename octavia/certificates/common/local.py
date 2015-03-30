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
Common classes for local filesystem certificate handling
"""
import os

from oslo_config import cfg

from octavia.certificates.common import cert

TLS_CERT_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_CA_CERT', '/etc/ssl/certs/ssl-cert-snakeoil.pem'
)
TLS_KEY_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_CA_KEY', '/etc/ssl/private/ssl-cert-snakeoil.key'
)
TLS_PKP_DEFAULT = os.environ.get('OS_OCTAVIA_CA_KEY_PASS')
TLS_DIGEST_DEFAULT = os.environ.get('OS_OCTAVIA_CA_SIGNING_DIGEST', 'sha256')
TLS_STORAGE_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_STORAGE', '/var/lib/octavia/certificates/'
)

certgen_opts = [
    cfg.StrOpt('ca_certificate',
               default=TLS_CERT_DEFAULT,
               help='Absolute path to the CA Certificate for signing. Defaults'
                    ' to env[OS_OCTAVIA_TLS_CA_CERT].'),
    cfg.StrOpt('ca_private_key',
               default=TLS_KEY_DEFAULT,
               help='Absolute path to the Private Key for signing. Defaults'
                    ' to env[OS_OCTAVIA_TLS_CA_KEY].'),
    cfg.StrOpt('ca_private_key_passphrase',
               default=TLS_PKP_DEFAULT,
               help='Passphrase for the Private Key. Defaults'
                    ' to env[OS_OCTAVIA_CA_KEY_PASS] or None.'),
    cfg.StrOpt('signing_digest',
               default=TLS_DIGEST_DEFAULT,
               help='Certificate signing digest. Defaults'
                    ' to env[OS_OCTAVIA_CA_SIGNING_DIGEST] or "sha256".')
]

certmgr_opts = [
    cfg.StrOpt('storage_path',
               default=TLS_STORAGE_DEFAULT,
               help='Absolute path to the certificate storage directory. '
                    'Defaults to env[OS_OCTAVIA_TLS_STORAGE].')
]

CONF = cfg.CONF
CONF.register_opts(certgen_opts, group='certificates')
CONF.register_opts(certmgr_opts, group='certificates')


class LocalCert(cert.Cert):
    """Representation of a Cert for local storage."""
    def __init__(self, certificate, private_key, intermediates=None,
                 private_key_passphrase=None):
        self.certificate = certificate
        self.intermediates = intermediates
        self.private_key = private_key
        self.private_key_passphrase = private_key_passphrase

    def get_certificate(self):
        return self.certificate

    def get_intermediates(self):
        return self.intermediates

    def get_private_key(self):
        return self.private_key

    def get_private_key_passphrase(self):
        return self.private_key_passphrase
