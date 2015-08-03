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
Cert manager implementation for Barbican
"""
from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils

from octavia.certificates.common import barbican as barbican_common
from octavia.certificates.manager import cert_mgr
from octavia.i18n import _LE, _LI, _LW


LOG = logging.getLogger(__name__)

CONF = cfg.CONF


class BarbicanCertManager(cert_mgr.CertManager):
    """Certificate Manager that wraps the Barbican client API."""
    @staticmethod
    def store_cert(certificate, private_key, intermediates=None,
                   private_key_passphrase=None, expiration=None,
                   name='Octavia TLS Cert'):
        """Stores a certificate in the certificate manager.

        :param certificate: PEM encoded TLS certificate
        :param private_key: private key for the supplied certificate
        :param intermediates: ordered and concatenated intermediate certs
        :param private_key_passphrase: optional passphrase for the supplied key
        :param expiration: the expiration time of the cert in ISO 8601 format
        :param name: a friendly name for the cert

        :returns: the container_ref of the stored cert
        :raises Exception: if certificate storage fails
        """
        connection = barbican_common.BarbicanAuth.get_barbican_client()

        LOG.info(_LI(
            "Storing certificate container '{0}' in Barbican."
        ).format(name))

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
                        LOG.info(_LI(
                            "Deleted secret {0} ({1}) during rollback."
                        ).format(i.name, old_ref))
                    except Exception:
                        LOG.warning(_LW(
                            "Failed to delete {0} ({1}) during rollback. This "
                            "might not be a problem."
                        ).format(i.name, old_ref))
            with excutils.save_and_reraise_exception():
                LOG.error(_LE(
                    "Error storing certificate data: {0}"
                ).format(str(e)))

    @staticmethod
    def get_cert(cert_ref, resource_ref=None, check_only=False,
                 service_name='Octavia'):
        """Retrieves the specified cert and registers as a consumer.

        :param cert_ref: the UUID of the cert to retrieve
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param check_only: Read Certificate data without registering
        :param service_name: Friendly name for the consuming service

        :return: octavia.certificates.common.Cert representation of the
                 certificate data
        :raises Exception: if certificate retrieval fails
        """
        connection = barbican_common.BarbicanAuth.get_barbican_client()

        LOG.info(_LI(
            "Loading certificate container {0} from Barbican."
        ).format(cert_ref))
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
            return barbican_common.BarbicanCert(cert_container)
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE(
                    "Error getting {0}: {1}"
                ).format(cert_ref, str(e)))

    @staticmethod
    def delete_cert(cert_ref, resource_ref=None, service_name='Octavia'):
        """Deregister as a consumer for the specified cert.

        :param cert_ref: the UUID of the cert to retrieve
        :param resource_ref: Full HATEOAS reference to the consuming resource
        :param service_name: Friendly name for the consuming service

        :raises Exception: if deregistration fails
        """
        connection = barbican_common.BarbicanAuth.get_barbican_client()

        LOG.info(_LI(
            "Deregistering as a consumer of {0} in Barbican."
        ).format(cert_ref))
        try:
            connection.containers.remove_consumer(
                container_ref=cert_ref,
                name=service_name,
                url=resource_ref
            )
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE(
                    "Error deregistering as a consumer of {0}: {1}"
                ).format(cert_ref, str(e)))

    @staticmethod
    def _actually_delete_cert(cert_ref):
        """Deletes the specified cert. Very dangerous. Do not recommend.

        :param cert_ref: the UUID of the cert to delete
        :raises Exception: if certificate deletion fails
        """
        connection = barbican_common.BarbicanAuth.get_barbican_client()

        LOG.info(_LI(
            "Recursively deleting certificate container {0} from Barbican."
        ).format(cert_ref))
        try:
            certificate_container = connection.containers.get(cert_ref)
            certificate_container.certificate.delete()
            if certificate_container.intermediates:
                certificate_container.intermediates.delete()
            if certificate_container.private_key_passphrase:
                certificate_container.private_key_passphrase.delete()
            certificate_container.private_key.delete()
            certificate_container.delete()
        except Exception as e:
            with excutils.save_and_reraise_exception():
                LOG.error(_LE(
                    "Error recursively deleting container {0}: {1}"
                ).format(cert_ref, str(e)))
