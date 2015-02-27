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
import binascii
import os

from OpenSSL import crypto
from oslo_config import cfg
from oslo_log import log as logging
import six

from octavia.certificates.common import local as local_common
from octavia.certificates.generator import cert_gen
from octavia.common import exceptions
from octavia.i18n import _LE, _LI


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class LocalCertGenerator(cert_gen.CertGenerator):
    """Cert Generator Interface that signs certs locally."""

    @classmethod
    def _new_serial(cls):
        return int(binascii.hexlify(os.urandom(20)), 16)

    @classmethod
    def _validate_cert(cls, ca_cert, ca_key, ca_key_pass):
        if not ca_cert:
            LOG.info(_LI("Using CA Certificate from config."))
            try:
                ca_cert = open(CONF.certificates.ca_certificate).read()
            except IOError:
                raise exceptions.CertificateGenerationException(
                    msg="Failed to load {0}."
                    .format(CONF.certificates.ca_certificate)
                )
        if not ca_key:
            LOG.info(_LI("Using CA Private Key from config."))
            try:
                ca_key = open(CONF.certificates.ca_private_key).read()
            except IOError:
                raise exceptions.CertificateGenerationException(
                    msg="Failed to load {0}."
                    .format(CONF.certificates.ca_certificate)
                )
        if not ca_key_pass:
            ca_key_pass = CONF.certificates.ca_private_key_passphrase
            if ca_key_pass:
                LOG.info(_LI(
                    "Using CA Private Key Passphrase from config."
                ))
            else:
                LOG.info(_LI(
                    "No Passphrase found for CA Private Key, not using one."
                ))

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
        LOG.info(_LI(
            "Signing a certificate request using pyOpenSSL locally."
        ))
        cls._validate_cert(ca_cert, ca_key, ca_key_pass)
        if not ca_digest:
            ca_digest = CONF.certificates.signing_digest
        if not ca_cert:
            with open(CONF.certificates.ca_certificate, 'r') as f:
                ca_cert = f.read()
        if not ca_key:
            with open(CONF.certificates.ca_private_key, 'r') as f:
                ca_key = f.read()
        if not ca_key_pass:
            ca_key_pass = CONF.certificates.ca_private_key_passphrase

        try:
            lo_cert = crypto.load_certificate(crypto.FILETYPE_PEM, ca_cert)
            lo_key = crypto.load_privatekey(crypto.FILETYPE_PEM, ca_key,
                                            ca_key_pass)
            lo_req = crypto.load_certificate_request(crypto.FILETYPE_PEM, csr)

            new_cert = crypto.X509()
            new_cert.set_version(2)
            new_cert.set_serial_number(cls._new_serial())
            new_cert.gmtime_adj_notBefore(0)
            new_cert.gmtime_adj_notAfter(validity)
            new_cert.set_issuer(lo_cert.get_subject())
            new_cert.set_subject(lo_req.get_subject())
            new_cert.set_pubkey(lo_req.get_pubkey())
            exts = [
                crypto.X509Extension(
                    six.b('basicConstraints'), True, six.b('CA:false')),
                crypto.X509Extension(
                    six.b('keyUsage'), True,
                    six.b('digitalSignature, keyEncipherment')),
                crypto.X509Extension(
                    six.b('extendedKeyUsage'), False,
                    six.b('clientAuth, serverAuth')),
                crypto.X509Extension(
                    six.b('nsCertType'), False,
                    six.b('client, server'))
            ]
            new_cert.add_extensions(exts)
            new_cert.sign(lo_key, ca_digest)

            return crypto.dump_certificate(crypto.FILETYPE_PEM, new_cert)
        except Exception as e:
            LOG.error(_LE("Unable to sign certificate."))
            raise exceptions.CertificateGenerationException(msg=e)

    @classmethod
    def _generate_private_key(cls, bit_length=2048, passphrase=None):
        pk = crypto.PKey()
        pk.generate_key(crypto.TYPE_RSA, bit_length)
        if passphrase:
            return crypto.dump_privatekey(
                crypto.FILETYPE_PEM,
                pk,
                'aes-256-cbc',
                passphrase
            )
        else:
            return crypto.dump_privatekey(
                crypto.FILETYPE_PEM,
                pk
            )

    @classmethod
    def _generate_csr(cls, cn, private_key, passphrase=None):
        if passphrase:
            pk = crypto.load_privatekey(
                crypto.FILETYPE_PEM,
                private_key,
                passphrase
            )
        else:
            pk = crypto.load_privatekey(
                crypto.FILETYPE_PEM,
                private_key
            )
        csr = crypto.X509Req()
        csr.set_pubkey(pk)
        subject = csr.get_subject()
        subject.CN = cn
        return crypto.dump_certificate_request(
            crypto.FILETYPE_PEM,
            csr
        )

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
