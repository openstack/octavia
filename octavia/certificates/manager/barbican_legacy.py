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
Legacy cert manager implementation for Barbican (container+secrets)
"""
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
from stevedore import driver as stevedore_driver

from octavia.certificates.common import barbican as barbican_common
from octavia.certificates.manager import cert_mgr
from octavia.common.tls_utils import cert_parser

LOG = logging.getLogger(__name__)


class BarbicanCertManager(cert_mgr.CertManager):
    """Certificate Manager that wraps the Barbican client API."""

    def __init__(self, auth=None):
        super(BarbicanCertManager, self).__init__()
        if auth:
            self.auth = auth
        else:
            self.auth = stevedore_driver.DriverManager(
                namespace='octavia.barbican_auth',
                name=cfg.CONF.certificates.barbican_auth,
                invoke_on_load=True,
            ).driver

    def store_cert(self, context, certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None, name=None):
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

        LOG.info("Storing certificate container '%s' in Barbican.", name)

        certificate_secret = None
        private_key_secret = None
        intermediates_secret = None
        pkp_secret = None

        try:
            certificate_secret = connection.secrets.create(
                payload=certificate,
                expiration=expiration,
                name="Certificate"
            )
            private_key_secret = connection.secrets.create(
                payload=private_key,
                expiration=expiration,
                name="Private Key"
            )
            certificate_container = connection.containers.create_certificate(
                name=name,
                certificate=certificate_secret,
                private_key=private_key_secret
            )
            if intermediates:
                intermediates_secret = connection.secrets.create(
                    payload=intermediates,
                    expiration=expiration,
                    name="Intermediates"
                )
                certificate_container.intermediates = intermediates_secret
            if private_key_passphrase:
                pkp_secret = connection.secrets.create(
                    payload=private_key_passphrase,
                    expiration=expiration,
                    name="Private Key Passphrase"
                )
                certificate_container.private_key_passphrase = pkp_secret

            certificate_container.store()
            return certificate_container.container_ref
        except Exception as e:
            for i in [certificate_secret, private_key_secret,
                      intermediates_secret, pkp_secret]:
                if i and i.secret_ref:
                    old_ref = i.secret_ref
                    try:
                        i.delete()
                        LOG.info('Deleted secret %s (%s) during rollback.',
                                 i.name, old_ref)
                    except Exception:
                        LOG.warning('Failed to delete %s (%s) during '
                                    'rollback. This might not be a problem.',
                                    i.name, old_ref)
            with excutils.save_and_reraise_exception():
                LOG.error('Error storing certificate data: %s', e)

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

        LOG.info('Loading certificate container %s from Barbican.', cert_ref)
        try:
            if check_only:
                cert_container = connection.containers.get(
                    container_ref=cert_ref
                )
            else:
                cert_container = connection.containers.register_consumer(
                    container_ref=cert_ref,
                    name=service_name,
                    url=resource_ref
                )
            barbican_cert = barbican_common.BarbicanCert(cert_container)

            LOG.debug('Validating certificate data for %s.', cert_ref)
            cert_parser.validate_cert(
                barbican_cert.get_certificate(),
                private_key=barbican_cert.get_private_key(),
                private_key_passphrase=(
                    barbican_cert.get_private_key_passphrase()),
                intermediates=barbican_cert.get_intermediates())
            LOG.debug('Certificate data validated for %s.', cert_ref)

            return barbican_cert
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error('Error getting cert %s: %s', cert_ref, str(e))

    def delete_cert(self, context, cert_ref, resource_ref, service_name=None):
        """Deregister as a consumer for the specified cert.

        :param context: Oslo context of the request
        :param cert_ref: the UUID of the cert to retrieve
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param service_name: Friendly name for the consuming service

        :raises Exception: if deregistration fails
        """
        connection = self.auth.get_barbican_client(context.project_id)

        LOG.info('Deregistering as a consumer of %s in Barbican.', cert_ref)
        try:
            connection.containers.remove_consumer(
                container_ref=cert_ref,
                name=service_name,
                url=resource_ref
            )
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error('Error deregistering as a consumer of %s: %s',
                          cert_ref, e)

    def set_acls(self, context, cert_ref):
        connection = self.auth.get_barbican_client(context.project_id)
        try:
            cert_container = connection.containers.get(
                container_ref=cert_ref
            )
        except Exception:
            # If the containers.get failed, it was probably because it isn't
            # legacy so we will skip this step
            return
        self.auth.ensure_secret_access(
            context, cert_container.certificate.secret_ref)
        self.auth.ensure_secret_access(
            context, cert_container.private_key.secret_ref)
        if cert_container.private_key_passphrase:
            self.auth.ensure_secret_access(
                context,
                cert_container.private_key_passphrase.secret_ref)
        if cert_container.intermediates:
            self.auth.ensure_secret_access(
                context, cert_container.intermediates.secret_ref)

    def unset_acls(self, context, cert_ref):
        connection = self.auth.get_barbican_client(context.project_id)
        try:
            cert_container = connection.containers.get(
                container_ref=cert_ref
            )
        except Exception:
            # If the containers.get failed, it was probably because it isn't
            # legacy so we will skip this step
            return
        self.auth.revoke_secret_access(
            context, cert_container.certificate.secret_ref)
        self.auth.revoke_secret_access(
            context, cert_container.private_key.secret_ref)
        if cert_container.private_key_passphrase:
            self.auth.revoke_secret_access(
                context,
                cert_container.private_key_passphrase.secret_ref)
        if cert_container.intermediates:
            self.auth.revoke_secret_access(
                context, cert_container.intermediates.secret_ref)
