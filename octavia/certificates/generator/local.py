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
import datetime
import uuid

from cryptography import exceptions as crypto_exceptions
from cryptography.hazmat import backends
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from oslo_config import cfg
from oslo_log import log as logging
import six

from octavia.certificates.common import local as local_common
from octavia.certificates.generator import cert_gen
from octavia.common import exceptions

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class LocalCertGenerator(cert_gen.CertGenerator):
    """Cert Generator Interface that signs certs locally."""

    @classmethod
    def _new_serial(cls):
        return int(uuid.uuid4())

    @classmethod
    def _validate_cert(cls, ca_cert, ca_key, ca_key_pass):
        if not ca_cert:
            LOG.info("Using CA Certificate from config.")
            try:
                ca_cert = open(CONF.certificates.ca_certificate, 'rb').read()
            except IOError:
                raise exceptions.CertificateGenerationException(
                    msg="Failed to load CA Certificate {0}."
                        .format(CONF.certificates.ca_certificate)
                )
        if not ca_key:
            LOG.info("Using CA Private Key from config.")
            try:
                ca_key = open(CONF.certificates.ca_private_key, 'rb').read()
            except IOError:
                raise exceptions.CertificateGenerationException(
                    msg="Failed to load CA Private Key {0}."
                        .format(CONF.certificates.ca_private_key)
                )
        if not ca_key_pass:
            ca_key_pass = CONF.certificates.ca_private_key_passphrase
            if ca_key_pass:
                LOG.info("Using CA Private Key Passphrase from config.")
            else:
                LOG.info("No Passphrase found for CA Private Key, not using "
                         "one.")

    @classmethod
    def sign_cert(cls, csr, validity, ca_cert=None, ca_key=None,
                  ca_key_pass=None, ca_digest=None):
        """Signs a certificate using our private CA based on the specified CSR

        The signed certificate will be valid from now until <validity> seconds
        from now.

        :param csr: A Certificate Signing Request
        :param validity: Valid for <validity> seconds from the current time
        :param ca_cert: Signing Certificate (default: config)
        :param ca_key: Signing Certificate Key (default: config)
        :param ca_key_pass: Signing Certificate Key Pass (default: config)
        :param ca_digest: Digest method to use for signing (default: config)

        :return: Signed certificate
        :raises Exception: if certificate signing fails
        """
        LOG.info("Signing a certificate request using OpenSSL locally.")
        cls._validate_cert(ca_cert, ca_key, ca_key_pass)
        if not ca_digest:
            ca_digest = CONF.certificates.signing_digest
        try:
            algorithm = getattr(hashes, ca_digest.upper())()
        except AttributeError:
            raise crypto_exceptions.UnsupportedAlgorithm(
                "Supplied digest method not found: %s" % ca_digest
            )

        if not ca_cert:
            with open(CONF.certificates.ca_certificate, 'rb') as f:
                ca_cert = f.read()
        if not ca_key:
            with open(CONF.certificates.ca_private_key, 'rb') as f:
                ca_key = f.read()
        if not ca_key_pass:
            ca_key_pass = CONF.certificates.ca_private_key_passphrase
            if ca_key_pass is not None:
                ca_key_pass = ca_key_pass.encode('utf-8')

        try:
            lo_cert = x509.load_pem_x509_certificate(
                data=ca_cert, backend=backends.default_backend())
            lo_key = serialization.load_pem_private_key(
                data=ca_key, password=ca_key_pass,
                backend=backends.default_backend())
            lo_req = x509.load_pem_x509_csr(data=csr,
                                            backend=backends.default_backend())
            new_cert = x509.CertificateBuilder()
            new_cert = new_cert.serial_number(cls._new_serial())
            valid_from_datetime = datetime.datetime.utcnow()
            valid_to_datetime = (datetime.datetime.utcnow() +
                                 datetime.timedelta(seconds=validity))
            new_cert = new_cert.not_valid_before(valid_from_datetime)
            new_cert = new_cert.not_valid_after(valid_to_datetime)
            new_cert = new_cert.issuer_name(lo_cert.subject)
            new_cert = new_cert.subject_name(lo_req.subject)
            new_cert = new_cert.public_key(lo_req.public_key())
            new_cert = new_cert.add_extension(
                x509.BasicConstraints(ca=False, path_length=None),
                critical=True
            )
            cn_str = lo_req.subject.get_attributes_for_oid(
                x509.oid.NameOID.COMMON_NAME)[0].value
            new_cert = new_cert.add_extension(
                x509.SubjectAlternativeName([x509.DNSName(cn_str)]),
                critical=False
            )
            new_cert = new_cert.add_extension(
                x509.KeyUsage(
                    digital_signature=True,
                    key_encipherment=True,
                    data_encipherment=True,
                    key_agreement=True,
                    content_commitment=False,
                    key_cert_sign=False,
                    crl_sign=False,
                    encipher_only=False,
                    decipher_only=False
                ),
                critical=True
            )
            new_cert = new_cert.add_extension(
                x509.ExtendedKeyUsage([
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
                ]),
                critical=True
            )
            signed_cert = new_cert.sign(private_key=lo_key,
                                        algorithm=algorithm,
                                        backend=backends.default_backend())
            return signed_cert.public_bytes(
                encoding=serialization.Encoding.PEM)
        except Exception as e:
            LOG.error("Unable to sign certificate.")
            raise exceptions.CertificateGenerationException(msg=e)

    @classmethod
    def _generate_private_key(cls, bit_length=2048, passphrase=None):
        pk = rsa.generate_private_key(
            public_exponent=65537,
            key_size=bit_length,
            backend=backends.default_backend()
        )
        if passphrase:
            encryption = serialization.BestAvailableEncryption(passphrase)
        else:
            encryption = serialization.NoEncryption()
        return pk.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=encryption,
        )

    @classmethod
    def _generate_csr(cls, cn, private_key, passphrase=None):
        cn = six.text_type(cn)
        pk = serialization.load_pem_private_key(
            data=private_key, password=passphrase,
            backend=backends.default_backend())
        csr = x509.CertificateSigningRequestBuilder().subject_name(
            x509.Name([
                x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, cn),
            ])
        )
        csr = csr.add_extension(
            x509.BasicConstraints(
                ca=False,
                path_length=None
            ),
            critical=True
        )
        csr = csr.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                data_encipherment=True,
                key_agreement=True,
                content_commitment=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False
            ),
            critical=True
        )
        csr = csr.add_extension(
            x509.SubjectAlternativeName([x509.DNSName(cn)]),
            critical=False
        )
        signed_csr = csr.sign(
            pk,
            getattr(hashes, CONF.certificates.signing_digest.upper())(),
            backends.default_backend())
        return signed_csr.public_bytes(serialization.Encoding.PEM)

    @classmethod
    def generate_cert_key_pair(cls, cn, validity, bit_length=2048,
                               passphrase=None, **kwargs):
        pk = cls._generate_private_key(bit_length, passphrase)
        csr = cls._generate_csr(cn, pk, passphrase)
        cert = cls.sign_cert(csr, validity, **kwargs)
        cert_object = local_common.LocalCert(
            certificate=cert,
            private_key=pk,
            private_key_passphrase=passphrase
        )
        return cert_object
