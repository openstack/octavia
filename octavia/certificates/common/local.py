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
from oslo_config import types as cfg_types

from octavia.certificates.common import cert

TLS_CERT_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_CA_CERT', '/etc/ssl/certs/ssl-cert-snakeoil.pem'
)
TLS_KEY_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_CA_KEY', '/etc/ssl/private/ssl-cert-snakeoil.key'
)
TLS_PKP_DEFAULT = os.environ.get('OS_OCTAVIA_CA_KEY_PASS')
TLS_PASS_AMPS_DEFAULT = os.environ.get('TLS_PASS_AMPS_DEFAULT',
                                       'insecure-key-do-not-use-this-key')

TLS_DIGEST_DEFAULT = os.environ.get('OS_OCTAVIA_CA_SIGNING_DIGEST', 'sha256')
TLS_STORAGE_DEFAULT = os.environ.get(
    'OS_OCTAVIA_TLS_STORAGE', '/var/lib/octavia/certificates/'
)


class FernetKeyOpt:
    regex_pattern = r'^[A-Za-z0-9\-_=]{32}$'

    def __init__(self, value: str):
        string_type = cfg_types.String(
            choices=None, regex=self.regex_pattern)
        self.value = string_type(value)

    def __repr__(self):
        return self.value.__repr__()

    def __str__(self):
        return self.value.__str__()


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
                    ' to env[OS_OCTAVIA_CA_KEY_PASS] or None.',
               secret=True),
    cfg.ListOpt('server_certs_key_passphrase',
                default=[TLS_PASS_AMPS_DEFAULT],
                item_type=FernetKeyOpt,
                help='List of passphrase for encrypting Amphora Certificates '
                'and Private Keys, first in list is used for encryption while '
                'all other keys is used to decrypt previously encrypted data. '
                'Each key must be 32, base64(url) compatible, characters long.'
                ' Defaults to env[TLS_PASS_AMPS_DEFAULT] or '
                'a list with default key insecure-key-do-not-use-this-key',
                required=True,
                secret=True),
    cfg.StrOpt('signing_digest',
               default=TLS_DIGEST_DEFAULT,
               help='Certificate signing digest. Defaults'
                    ' to env[OS_OCTAVIA_CA_SIGNING_DIGEST] or "sha256".'),
    cfg.IntOpt('cert_validity_time',
               default=30 * 24 * 60 * 60,
               help="The validity time for the Amphora Certificates "
                    "(in seconds)."),
]

certmgr_opts = [
    cfg.StrOpt('storage_path',
               default=TLS_STORAGE_DEFAULT,
               help='Absolute path to the certificate storage directory. '
                    'Defaults to env[OS_OCTAVIA_TLS_STORAGE].')
]


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
