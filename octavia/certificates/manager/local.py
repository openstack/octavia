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
import os
import uuid

from oslo_config import cfg
from oslo_log import log as logging

from octavia.certificates.common import local as local_common
from octavia.certificates.manager import cert_mgr
from octavia.common import exceptions
from octavia.i18n import _LE, _LI

LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class LocalCertManager(cert_mgr.CertManager):
    """Cert Manager Interface that stores data locally."""

    @staticmethod
    def store_cert(certificate, private_key, intermediates=None,
                   private_key_passphrase=None, **kwargs):
        """Stores (i.e., registers) a cert with the cert manager.

        This method stores the specified cert to the filesystem and returns
        a UUID that can be used to retrieve it.

        :param certificate: PEM encoded TLS certificate
        :param private_key: private key for the supplied certificate
        :param intermediates: ordered and concatenated intermediate certs
        :param private_key_passphrase: optional passphrase for the supplied key

        :returns: the UUID of the stored cert
        :raises CertificateStorageException: if certificate storage fails
        """
        cert_ref = str(uuid.uuid4())
        filename_base = os.path.join(CONF.certificates.storage_path, cert_ref)

        LOG.info(_LI(
            "Storing certificate data on the local filesystem."
        ))
        try:
            filename_certificate = "{0}.crt".format(filename_base, cert_ref)
            with open(filename_certificate, 'w') as cert_file:
                cert_file.write(certificate)

            filename_private_key = "{0}.key".format(filename_base, cert_ref)
            with open(filename_private_key, 'w') as key_file:
                key_file.write(private_key)

            if intermediates:
                filename_intermediates = "{0}.int".format(filename_base,
                                                          cert_ref)
                with open(filename_intermediates, 'w') as int_file:
                    int_file.write(intermediates)

            if private_key_passphrase:
                filename_pkp = "{0}.pass".format(filename_base, cert_ref)
                with open(filename_pkp, 'w') as pass_file:
                    pass_file.write(private_key_passphrase)
        except IOError as ioe:
            LOG.error(_LE("Failed to store certificate."))
            raise exceptions.CertificateStorageException(message=ioe.message)

        return cert_ref

    @staticmethod
    def get_cert(cert_ref, **kwargs):
        """Retrieves the specified cert.

        :param cert_ref: the UUID of the cert to retrieve

        :return: octavia.certificates.common.Cert representation of the
                 certificate data
        :raises CertificateStorageException: if certificate retrieval fails
        """
        LOG.info(_LI(
            "Loading certificate {0} from the local filesystem."
        ).format(cert_ref))

        filename_base = os.path.join(CONF.certificates.storage_path, cert_ref)

        filename_certificate = "{0}.crt".format(filename_base, cert_ref)
        filename_private_key = "{0}.key".format(filename_base, cert_ref)
        filename_intermediates = "{0}.int".format(filename_base, cert_ref)
        filename_pkp = "{0}.pass".format(filename_base, cert_ref)

        cert_data = dict()

        try:
            with open(filename_certificate, 'r') as cert_file:
                cert_data['certificate'] = cert_file.read()
        except IOError:
            LOG.error(_LE(
                "Failed to read certificate for {0}."
            ).format(cert_ref))
            raise exceptions.CertificateStorageException(
                msg="Certificate could not be read."
            )
        try:
            with open(filename_private_key, 'r') as key_file:
                cert_data['private_key'] = key_file.read()
        except IOError:
            LOG.error(_LE(
                "Failed to read private key for {0}."
            ).format(cert_ref))
            raise exceptions.CertificateStorageException(
                msg="Private Key could not be read."
            )

        try:
            with open(filename_intermediates, 'r') as int_file:
                cert_data['intermediates'] = int_file.read()
        except IOError:
            pass

        try:
            with open(filename_pkp, 'r') as pass_file:
                cert_data['private_key_passphrase'] = pass_file.read()
        except IOError:
            pass

        return local_common.LocalCert(**cert_data)

    @staticmethod
    def delete_cert(cert_ref, **kwargs):
        """Deletes the specified cert.

        :param cert_ref: the UUID of the cert to delete

        :raises CertificateStorageException: if certificate deletion fails
        """
        LOG.info(_LI(
            "Deleting certificate {0} from the local filesystem."
        ).format(cert_ref))

        filename_base = os.path.join(CONF.certificates.storage_path, cert_ref)

        filename_certificate = "{0}.crt".format(filename_base, cert_ref)
        filename_private_key = "{0}.key".format(filename_base, cert_ref)
        filename_intermediates = "{0}.int".format(filename_base, cert_ref)
        filename_pkp = "{0}.pass".format(filename_base, cert_ref)

        try:
            os.remove(filename_certificate)
            os.remove(filename_private_key)
            os.remove(filename_intermediates)
            os.remove(filename_pkp)
        except IOError as ioe:
            LOG.error(_LE(
                "Failed to delete certificate {0}."
            ).format(cert_ref))
            raise exceptions.CertificateStorageException(message=ioe.message)
