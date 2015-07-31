#
# Copyright 2014 Rackspace.  All rights reserved
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

from cryptography.hazmat import backends
from cryptography import x509
from OpenSSL import crypto
from OpenSSL import SSL
from oslo_log import log as logging
import six

from octavia.common import data_models as data_models
import octavia.common.exceptions as exceptions


X509_BEG = "-----BEGIN CERTIFICATE-----"
X509_END = "-----END CERTIFICATE-----"

LOG = logging.getLogger(__name__)


def validate_cert(certificate, private_key=None,
                  private_key_passphrase=None, intermediates=None):
    """Validate that the certificate is a valid PEM encoded X509 object

    Optionally verify that the private key matches the certificate.
    Optionally verify that the intermediates are valid X509 objects.

    :param certificate: A PEM encoded certificate
    :param private_key: The private key for the certificate
    :param private_key_passphrase: Passphrase for accessing the private key
    :param intermediates: PEM encoded intermediate certificates
    :returns: boolean
    """
    x509 = _get_x509_from_pem_bytes(certificate)
    if intermediates:
        for x509pem in _split_x509s(intermediates):
            _get_x509_from_pem_bytes(x509pem)
    if private_key:
        pkey = _read_privatekey(
            private_key, passphrase=private_key_passphrase)
        ctx = SSL.Context(SSL.TLSv1_METHOD)
        ctx.use_certificate(x509)
        try:
            ctx.use_privatekey(pkey)
            ctx.check_privatekey()
        except Exception:
            raise exceptions.MisMatchedKey
    return True


def _read_privatekey(privatekey_pem, passphrase=None):
    def _get_passphrase(*args):
        if passphrase:
            return six.b(passphrase)
        else:
            raise exceptions.NeedsPassphrase
    return crypto.load_privatekey(crypto.FILETYPE_PEM, privatekey_pem,
                                  _get_passphrase)


def _split_x509s(xstr):
    """Split the input string into individual x509 text blocks

    :param xstr: A large multi x509 certificate blcok
    :returns: A list of strings where each string represents an
    X509 pem block surrounded by BEGIN CERTIFICATE,
    END CERTIFICATE block tags
    """
    curr_pem_block = []
    inside_x509 = False
    for line in xstr.replace("\r", "").split("\n"):
        if inside_x509:
            curr_pem_block.append(line)
            if line == X509_END:
                yield "\n".join(curr_pem_block)
                curr_pem_block = []
                inside_x509 = False
            continue
        else:
            if line == X509_BEG:
                curr_pem_block.append(line)
                inside_x509 = True


def get_host_names(certificate):
    """Extract the host names from the Pem encoded X509 certificate

    :param certificate: A PEM encoded certificate
    :returns: A dictionary containing the following keys:
    ['cn', 'dns_names']
    where 'cn' is the CN from the SubjectName of the certificate, and
    'dns_names' is a list of dNSNames (possibly empty) from
    the SubjectAltNames of the certificate.
    """
    try:
        certificate = certificate.encode('ascii')
        cert = x509.load_pem_x509_certificate(certificate,
                                              backends.default_backend())
        cn = cert.subject.get_attributes_for_oid(x509.OID_COMMON_NAME)[0]
        host_names = {
            'cn': cn.value.lower(),
            'dns_names': []
        }
        try:
            ext = cert.extensions.get_extension_for_oid(
                x509.OID_SUBJECT_ALTERNATIVE_NAME
            )
            host_names['dns_names'] = ext.value.get_values_for_type(
                x509.DNSName)
        except x509.ExtensionNotFound:
            LOG.debug("{0} extension not found".format(
                x509.OID_SUBJECT_ALTERNATIVE_NAME))

        return host_names
    except Exception as e:
        LOG.exception(e)
        raise exceptions.UnreadableCert


def _get_x509_from_pem_bytes(certificate_pem):
    """Parse X509 data from a PEM encoded certificate

    :param certificate_pem: Certificate in PEM format
    :returns: pyOpenSSL high-level x509 data from the PEM string
    """
    try:
        x509 = crypto.load_certificate(crypto.FILETYPE_PEM,
                                       certificate_pem)
    except Exception:
        raise exceptions.UnreadableCert
    return x509


def build_pem(tls_container):
        """Concatenate TLS container fields to create a PEM

        encoded certificate file

        :param tls_container: Object container TLS certificates
        :returns: Pem encoded certificate file
        """
        pem = []
        if tls_container.intermediates:
            pem = tls_container.intermediates[:]
        pem.extend([tls_container.certificate, tls_container.private_key])
        return "\n".join(pem)


def load_certificates_data(cert_mngr, listener):
        """Load TLS certificate data from the listener.

        return TLS_CERT and SNI_CERTS
        """
        tls_cert = None
        sni_certs = []

        if listener.tls_certificate_id:
            tls_cert = _map_cert_tls_container(
                cert_mngr.get_cert(listener.tls_certificate_id,
                                   check_only=True))
        if listener.sni_containers:
            for sni_cont in listener.sni_containers:
                cert_container = _map_cert_tls_container(
                    cert_mngr.get_cert(sni_cont.tls_container.id,
                                       check_only=True))
                sni_certs.append(cert_container)
        return {'tls_cert': tls_cert, 'sni_certs': sni_certs}


def _map_cert_tls_container(cert):
        return data_models.TLSContainer(
            primary_cn=get_primary_cn(cert),
            private_key=cert.get_private_key(),
            certificate=cert.get_certificate(),
            intermediates=cert.get_intermediates())


def get_primary_cn(tls_cert):
        """Returns primary CN for Certificate."""
        return get_host_names(tls_cert.get_certificate())['cn']
