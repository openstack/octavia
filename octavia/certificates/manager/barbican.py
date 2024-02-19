# Copyright (c) 2014 Rackspace US, Inc
# Copyright (c) 2017 GoDaddy
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
Cert manager implementation for Barbican using a single PKCS12 secret
"""
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12 as c_pkcs12
from cryptography import x509
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import encodeutils
from oslo_utils import excutils
from stevedore import driver as stevedore_driver

from octavia.certificates.common import pkcs12
from octavia.certificates.manager import barbican_legacy
from octavia.certificates.manager import cert_mgr
from octavia.common import exceptions
from octavia.common.tls_utils import cert_parser

LOG = logging.getLogger(__name__)


class BarbicanCertManager(cert_mgr.CertManager):
    """Certificate Manager that wraps the Barbican client API."""

    def __init__(self):
        super().__init__()
        self.auth = stevedore_driver.DriverManager(
            namespace='octavia.barbican_auth',
            name=cfg.CONF.certificates.barbican_auth,
            invoke_on_load=True,
        ).driver

    def store_cert(self, context, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name="PKCS12 Certificate Bundle"):
        """Stores a certificate in the certificate manager.

        :param context: Oslo context of the request
        :param certificate: PEM encoded TLS certificate
        :param private_key: private key for the supplied certificate
        :param intermediates: ordered and concatenated intermediate certs
        :param private_key_passphrase: optional passphrase for the supplied key
        :param expiration: the expiration time of the cert in ISO 8601 format
        :param name: a friendly name for the cert

        :returns: the container_ref of the stored cert
        :raises Exception: if certificate storage fails
        """
        connection = self.auth.get_barbican_client(context.project_id)

        LOG.info("Storing certificate secret '%s' in Barbican.", name)

        if private_key_passphrase:
            raise exceptions.CertificateStorageException(
                "Passphrase protected PKCS12 certificates are not supported.")

        x509_cert = x509.load_pem_x509_certificate(certificate)
        x509_pk = serialization.load_pem_private_key(private_key, None)
        cas = None
        if intermediates:
            cert_ints = list(cert_parser.get_intermediates_pems(intermediates))
            cas = [
                x509.load_pem_x509_certificate(ci)
                for ci in cert_ints]

        try:
            certificate_secret = connection.secrets.create(
                payload=c_pkcs12.serialize_key_and_certificates(
                    name=encodeutils.safe_encode(name),
                    key=x509_pk,
                    cert=x509_cert,
                    cas=cas,
                    encryption_algorithm=serialization.NoEncryption()
                ),
                expiration=expiration,
                name=name
            )
            certificate_secret.store()
            return certificate_secret.secret_ref
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error('Error storing certificate data: %s', str(e))
        return None

    def get_cert(self, context, cert_ref, resource_ref=None, check_only=False,
                 service_name=None):
        """Retrieves the specified cert and registers as a consumer.

        :param context: Oslo context of the request
        :param cert_ref: the UUID of the cert to retrieve
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param check_only: Read Certificate data without registering
        :param service_name: Friendly name for the consuming service

        :return: octavia.certificates.common.Cert representation of the
                 certificate data
        :raises Exception: if certificate retrieval fails
        """
        connection = self.auth.get_barbican_client(context.project_id)

        LOG.info('Loading certificate secret %s from Barbican.', cert_ref)
        try:
            cert_secret = connection.secrets.get(secret_ref=cert_ref)
            return pkcs12.PKCS12Cert(cert_secret.payload)
        except exceptions.UnreadablePKCS12:
            raise
        except Exception as e:
            LOG.warning('Failed to load PKCS12Cert for secret %s with %s',
                        cert_ref, str(e))
            LOG.warning('Falling back to the barbican_legacy implementation.')
            # If our get fails, try with the legacy driver.
            # TODO(rm_work): Remove this code when the deprecation cycle for
            # the legacy driver is complete.
            legacy_mgr = barbican_legacy.BarbicanCertManager()
            legacy_cert = legacy_mgr.get_cert(
                context, cert_ref, resource_ref=resource_ref,
                check_only=check_only, service_name=service_name
            )
            return legacy_cert

    def delete_cert(self, context, cert_ref, resource_ref, service_name=None):
        """Deregister as a consumer for the specified cert.

        :param context: Oslo context of the request
        :param cert_ref: the UUID of the cert to retrieve
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param service_name: Friendly name for the consuming service

        :raises Exception: if deregistration fails
        """
        # TODO(rm_work): We won't take any action on a delete in this driver,
        # but for now try the legacy driver's delete and ignore failure.
        try:
            legacy_mgr = barbican_legacy.BarbicanCertManager(auth=self.auth)
            legacy_mgr.delete_cert(
                context, cert_ref, resource_ref, service_name=service_name)
        except Exception:
            # If the delete failed, it was probably because it isn't legacy
            # (this will be fixed once Secrets have Consumer registration).
            pass

    def set_acls(self, context, cert_ref):
        LOG.debug('Setting project ACL for certificate secret...')
        self.auth.ensure_secret_access(context, cert_ref)
        # TODO(velizarx): Remove this code when the deprecation cycle for
        # the legacy driver is complete.
        legacy_mgr = barbican_legacy.BarbicanCertManager(auth=self.auth)
        legacy_mgr.set_acls(context, cert_ref)

    def unset_acls(self, context, cert_ref):
        LOG.debug('Unsetting project ACL for certificate secret...')
        self.auth.revoke_secret_access(context, cert_ref)
        # TODO(velizarx): Remove this code when the deprecation cycle for
        # the legacy driver is complete.
        legacy_mgr = barbican_legacy.BarbicanCertManager(auth=self.auth)
        legacy_mgr.unset_acls(context, cert_ref)

    def get_secret(self, context, secret_ref):
        """Retrieves a secret payload by reference.

        :param context: Oslo context of the request
        :param secret_ref: The secret reference ID

        :return: The secret payload
        :raises CertificateStorageException: if retrieval fails
        """
        connection = self.auth.get_barbican_client(context.project_id)

        LOG.info('Loading secret %s from Barbican.', secret_ref)
        try:
            secret = connection.secrets.get(secret_ref=secret_ref)
            return secret.payload
        except Exception as e:
            LOG.error("Failed to access secret for %s due to: %s.",
                      secret_ref, str(e))
            raise exceptions.CertificateRetrievalException(ref=secret_ref)
