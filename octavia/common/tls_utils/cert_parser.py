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

import base64
import hashlib

from cryptography.hazmat import backends
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from oslo_context import context as oslo_context
from oslo_log import log as logging
from pyasn1.codec.der import decoder as der_decoder
from pyasn1.codec.der import encoder as der_encoder
from pyasn1_modules import rfc2315
import six

from octavia.common import data_models
import octavia.common.exceptions as exceptions

X509_BEG = b'-----BEGIN CERTIFICATE-----'
X509_END = b'-----END CERTIFICATE-----'
PKCS7_BEG = b'-----BEGIN PKCS7-----'
PKCS7_END = b'-----END PKCS7-----'

LOG = logging.getLogger(__name__)


def validate_cert(certificate, private_key=None,
                  private_key_passphrase=None, intermediates=None):
    """Validate that the certificate is a valid PEM encoded X509 object

    Optionally verify that the private key matches the certificate.
    Optionally verify that the intermediates are valid X509 objects.

    :param certificate: A PEM encoded certificate
    :param private_key: The private key for the certificate
    :param private_key_passphrase: Passphrase for accessing the private key
    :param intermediates: PEM or PKCS7 encoded intermediate certificates
    :returns: boolean
    """
    cert = _get_x509_from_pem_bytes(certificate)
    if intermediates and not isinstance(intermediates, list):
        # If the intermediates are in a list, then they are already loaded.
        # Load the certificates to validate them, if they weren't already.
        list(get_intermediates_pems(intermediates))
    if private_key:
        pkey = _read_private_key(private_key,
                                 passphrase=private_key_passphrase)
        pknum = pkey.public_key().public_numbers()
        certnum = cert.public_key().public_numbers()
        if pknum != certnum:
            raise exceptions.MisMatchedKey
    return True


def _read_private_key(private_key_pem, passphrase=None):
    """Reads a private key PEM block and returns a RSAPrivatekey

    :param private_key_pem: The private key PEM block
    :param passphrase: Optional passphrase needed to decrypt the private key
    :returns: a RSAPrivatekey object
    """
    if passphrase and type(passphrase) == six.text_type:
        passphrase = passphrase.encode("utf-8")
    if type(private_key_pem) == six.text_type:
        private_key_pem = private_key_pem.encode('utf-8')

    try:
        return serialization.load_pem_private_key(private_key_pem, passphrase,
                                                  backends.default_backend())
    except Exception:
        LOG.exception("Passphrase required.")
        raise exceptions.NeedsPassphrase


def prepare_private_key(private_key, passphrase=None):
    """Prepares an unencrypted PEM-encoded private key for printing

    :param private_key: The private key in PEM format (encrypted or not)
    :returns: The unencrypted private key in PEM format
    """
    pk = _read_private_key(private_key, passphrase)
    return pk.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()).strip()


def get_intermediates_pems(intermediates=None):
    """Split the input string into individual x509 text blocks

    :param intermediates: PEM or PKCS7 encoded intermediate certificates
    :returns: A list of strings where each string represents an
              X509 pem block surrounded by BEGIN CERTIFICATE,
              END CERTIFICATE block tags
    """
    if X509_BEG in intermediates:
        for x509Pem in _split_x509s(intermediates):
            yield _prepare_x509_cert(_get_x509_from_pem_bytes(x509Pem))
    else:
        for x509Pem in _parse_pkcs7_bundle(intermediates):
            yield _prepare_x509_cert(_get_x509_from_der_bytes(x509Pem))


def _prepare_x509_cert(cert=None):
    """Prepares a PEM-encoded X509 certificate for printing

    :param intermediates: X509Certificate object
    :returns: A PEM-encoded X509 certificate
    """
    return cert.public_bytes(encoding=serialization.Encoding.PEM).strip()


def _split_x509s(xstr):
    """Split the input string into individual x509 text blocks

    :param xstr: A large multi x509 certificate blcok
    :returns: A list of strings where each string represents an
    X509 pem block surrounded by BEGIN CERTIFICATE,
    END CERTIFICATE block tags
    """
    curr_pem_block = []
    inside_x509 = False
    if type(xstr) == six.binary_type:
        xstr = xstr.decode('utf-8')
    for line in xstr.replace("\r", "").split("\n"):
        if inside_x509:
            curr_pem_block.append(line)
            if line == X509_END.decode('utf-8'):
                yield six.b("\n".join(curr_pem_block))
                curr_pem_block = []
                inside_x509 = False
            continue
        else:
            if line == X509_BEG.decode('utf-8'):
                curr_pem_block.append(line)
                inside_x509 = True


def _parse_pkcs7_bundle(pkcs7):
    """Parse a PKCS7 certificate bundle in DER or PEM format

    :param pkcs7: A pkcs7 bundle in DER or PEM format
    :returns: A list of individual DER-encoded certificates
    """
    # Look for PEM encoding
    if PKCS7_BEG in pkcs7:
        try:
            for substrate in _read_pem_blocks(pkcs7):
                for cert in _get_certs_from_pkcs7_substrate(substrate):
                    yield cert
        except Exception:
            LOG.exception('Unreadable Certificate.')
            raise exceptions.UnreadableCert

    # If no PEM encoding, assume this is DER encoded and try to decode
    else:
        for cert in _get_certs_from_pkcs7_substrate(pkcs7):
            yield cert


def _read_pem_blocks(data):
    """Parse a series of PEM-encoded blocks

    This method is based on pyasn1-modules.pem.readPemBlocksFromFile, but
    eliminates the need to operate on a file handle and is a generator.

    :param data: A long text string containing one or more PEM-encoded blocks
    :param markers: A tuple containing the test strings that indicate the
                    start and end of the PEM-encoded blocks
    :returns: An ASN1 substrate suitable for DER decoding.

    """
    stSpam, stHam, stDump = 0, 1, 2
    startMarkers = {PKCS7_BEG.decode('utf-8'): 0}
    stopMarkers = {PKCS7_END.decode('utf-8'): 0}
    idx = -1
    state = stSpam
    if type(data) == six.binary_type:
        data = data.decode('utf-8')
    for certLine in data.replace('\r', '').split('\n'):
        if not certLine:
            continue
        certLine = certLine.strip()
        if state == stSpam:
            if certLine in startMarkers:
                certLines = []
                idx = startMarkers[certLine]
                state = stHam
                continue
        if state == stHam:
            if certLine in stopMarkers and stopMarkers[certLine] == idx:
                state = stDump
            else:
                certLines.append(certLine)
        if state == stDump:
            yield b''.join([base64.b64decode(x) for x in certLines])
            state = stSpam


def _get_certs_from_pkcs7_substrate(substrate):
    """Extracts DER-encoded X509 certificates from a PKCS7 ASN1 DER substrate

    :param substrate: The substrate to be processed
    :returns: A list of DER-encoded X509 certificates
    """
    try:
        contentInfo, _ = der_decoder.decode(substrate,
                                            asn1Spec=rfc2315.ContentInfo())
        contentType = contentInfo.getComponentByName('contentType')
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert
    if contentType != rfc2315.signedData:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert

    try:
        content, _ = der_decoder.decode(
            contentInfo.getComponentByName('content'),
            asn1Spec=rfc2315.SignedData())
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert

    for cert in content.getComponentByName('certificates'):
        yield der_encoder.encode(cert)


def get_host_names(certificate):
    """Extract the host names from the Pem encoded X509 certificate

    :param certificate: A PEM encoded certificate
    :returns: A dictionary containing the following keys:
              ['cn', 'dns_names']
              where 'cn' is the CN from the SubjectName of the
              certificate, and 'dns_names' is a list of dNSNames
              (possibly empty) from the SubjectAltNames of the certificate.
    """
    try:
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
            LOG.debug("%s extension not found",
                      x509.OID_SUBJECT_ALTERNATIVE_NAME)

        return host_names
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert


def get_cert_expiration(certificate_pem):
    """Extract the expiration date from the Pem encoded X509 certificate

    :param certificate_pem: Certificate in PEM format
    :returns: Expiration date of certificate_pem
    """
    try:
        cert = x509.load_pem_x509_certificate(certificate_pem,
                                              backends.default_backend())
        return cert.not_valid_after
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert


def _get_x509_from_pem_bytes(certificate_pem):
    """Parse X509 data from a PEM encoded certificate

    :param certificate_pem: Certificate in PEM format
    :returns: crypto high-level x509 data from the PEM string
    """
    if type(certificate_pem) == six.text_type:
        certificate_pem = certificate_pem.encode('utf-8')
    try:
        x509cert = x509.load_pem_x509_certificate(certificate_pem,
                                                  backends.default_backend())
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert
    return x509cert


def _get_x509_from_der_bytes(certificate_der):
    """Parse X509 data from a DER encoded certificate

    :param certificate_der: Certificate in DER format
    :returns: crypto high-level x509 data from the DER-encoded certificate
    """
    try:
        x509cert = x509.load_der_x509_certificate(certificate_der,
                                                  backends.default_backend())
    except Exception:
        LOG.exception('Unreadable Certificate.')
        raise exceptions.UnreadableCert
    return x509cert


def build_pem(tls_container):
    """Concatenate TLS container fields to create a PEM

    encoded certificate file

    :param tls_container: Object container TLS certificates
    :returns: Pem encoded certificate file
    """
    pem = [tls_container.certificate]
    if tls_container.private_key:
        pem.append(tls_container.private_key)
    if tls_container.intermediates:
        pem.extend(tls_container.intermediates[:])
    return b'\n'.join(pem) + b'\n'


def load_certificates_data(cert_mngr, obj, context=None):
    """Load TLS certificate data from the listener/pool.

    return TLS_CERT and SNI_CERTS
    """
    tls_cert = None
    sni_certs = []
    if not context:
        context = oslo_context.RequestContext(project_id=obj.project_id)

    if obj.tls_certificate_id:
        tls_cert = _map_cert_tls_container(
            cert_mngr.get_cert(context,
                               obj.tls_certificate_id,
                               check_only=True))
    if hasattr(obj, 'sni_containers') and obj.sni_containers:
        for sni_cont in obj.sni_containers:
            cert_container = _map_cert_tls_container(
                cert_mngr.get_cert(context,
                                   sni_cont.tls_container_id,
                                   check_only=True))
            sni_certs.append(cert_container)
    return {'tls_cert': tls_cert, 'sni_certs': sni_certs}


def _map_cert_tls_container(cert):
    return data_models.TLSContainer(
        # TODO(rm_work): applying nosec here because this is not intended to be
        # secure, it's just a way to get a consistent ID. Changing this would
        # break backwards compatibility with existing loadbalancers.
        id=hashlib.sha1(cert.get_certificate()).hexdigest(),  # nosec
        primary_cn=get_primary_cn(cert),
        private_key=prepare_private_key(
            cert.get_private_key(),
            cert.get_private_key_passphrase()),
        certificate=cert.get_certificate(),
        intermediates=cert.get_intermediates())


def get_primary_cn(tls_cert):
    """Returns primary CN for Certificate."""
    return get_host_names(tls_cert.get_certificate())['cn']
