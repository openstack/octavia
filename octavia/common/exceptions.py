# Copyright 2011 VMware, Inc, 2014 A10 Networks
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
Octavia base exception handling.
"""

import six

from oslo_utils import excutils
from webob import exc

from octavia.i18n import _


class OctaviaException(Exception):
    """Base Octavia Exception.

    To correctly use this class, inherit from it and define
    a 'message' property. That message will get printf'd
    with the keyword arguments provided to the constructor.
    """
    message = _("An unknown exception occurred.")
    orig_msg = None
    orig_code = None

    def __init__(self, *args, **kwargs):
        try:
            if args:
                self.message = args[0]
                self.orig_msg = kwargs.get('orig_msg')
                self.orig_code = kwargs.get('orig_code')
            super(OctaviaException, self).__init__(self.message % kwargs)
            self.msg = self.message % kwargs
        except Exception:
            with excutils.save_and_reraise_exception() as ctxt:
                if not self.use_fatal_exceptions():
                    ctxt.reraise = False
                    # at least get the core message out if something happened
                    super(OctaviaException, self).__init__(self.message)

    def __unicode__(self):
        return six.text_type(self.msg)

    @staticmethod
    def use_fatal_exceptions():
        return False


# NOTE(blogan) Using webob exceptions here because WSME exceptions a very
# limited at this point and they do not work well in _lookup methods in the
# controllers
class APIException(exc.HTTPClientError):
    msg = "Something unknown went wrong"
    code = 500

    def __init__(self, **kwargs):
        self.msg = self.msg % kwargs
        super(APIException, self).__init__(detail=self.msg)


class NotFound(APIException):
    msg = _('%(resource)s %(id)s not found.')
    code = 404


class PolicyForbidden(APIException):
    msg = _("Policy does not allow this request to be performed.")
    code = 403


class InvalidOption(APIException):
    msg = _("%(value)s is not a valid option for %(option)s")
    code = 400


class InvalidFilterArgument(APIException):
    msg = "One or more arguments are either duplicate or invalid"
    code = 400


class DisabledOption(APIException):
    msg = _("The selected %(option)s is not allowed in this deployment: "
            "%(value)s")
    code = 400


class L7RuleValidation(APIException):
    msg = _("Error parsing L7Rule: %(error)s")
    code = 400


class SingleCreateDetailsMissing(APIException):
    msg = _("Missing details for %(type)s object: %(name)")
    code = 400


class InvalidHMACException(OctaviaException):
    message = _("HMAC hashes didn't match")


class MissingArguments(OctaviaException):
    message = _("Missing arguments.")


class NetworkConfig(OctaviaException):
    message = _("Unable to allocate network resource from config")


class NeedsPassphrase(OctaviaException):
    message = _("Passphrase needed to decrypt key but client "
                "did not provide one.")


class UnreadableCert(OctaviaException):
    message = _("Could not read X509 from PEM")


class MisMatchedKey(OctaviaException):
    message = _("Key and x509 certificate do not match")


class CertificateRetrievalException(APIException):
    msg = _('Could not retrieve certificate: %(ref)s')
    code = 400


class CertificateStorageException(OctaviaException):
    message = _('Could not store certificate: %(msg)s')


class CertificateGenerationException(OctaviaException):
    message = _('Could not sign the certificate request: %(msg)s')


class DuplicateListenerEntry(APIException):
    msg = _("Another Listener on this Load Balancer "
            "is already using protocol_port %(port)d")
    code = 409


class DuplicateMemberEntry(APIException):
    msg = _("Another member on this pool is already using ip %(ip_address)s "
            "on protocol_port %(port)d")
    code = 409


class DuplicateHealthMonitor(APIException):
    msg = _("This pool already has a health monitor")
    code = 409


class DuplicatePoolEntry(APIException):
    msg = _("This listener already has a default pool")
    code = 409


class PoolInUseByL7Policy(APIException):
    msg = _("Pool %(id)s is in use by L7 policy %(l7policy_id)s")
    code = 409


class ImmutableObject(APIException):
    msg = _("%(resource)s %(id)s is immutable and cannot be updated.")
    code = 409


class LBPendingStateError(APIException):
    msg = _("Invalid state %(state)s of loadbalancer resource %(id)s")
    code = 409


class TooManyL7RulesOnL7Policy(APIException):
    msg = _("Too many rules on L7 policy %(id)s")
    code = 409


class ComputeBuildException(OctaviaException):
    message = _("Failed to build compute instance due to: %(fault)s")


class ComputeBuildQueueTimeoutException(OctaviaException):
    message = _('Failed to get an amphora build slot.')


class ComputeDeleteException(OctaviaException):
    message = _('Failed to delete compute instance.')


class ComputeGetException(OctaviaException):
    message = _('Failed to retrieve compute instance.')


class ComputeStatusException(OctaviaException):
    message = _('Failed to retrieve compute instance status.')


class ComputeGetInterfaceException(OctaviaException):
    message = _('Failed to retrieve compute virtual interfaces.')


class IDAlreadyExists(APIException):
    msg = _('Already an entity with that specified id.')
    code = 409


class NoReadyAmphoraeException(OctaviaException):
    message = _('There are not any READY amphora available.')


class GlanceNoTaggedImages(OctaviaException):
    message = _("No Glance images are tagged with %(tag)s tag.")


# This is an internal use exception for the taskflow work flow
# and will not be exposed to the customer.  This means it is a
# normal part of operation while waiting for compute to go active
# on the instance
class ComputeWaitTimeoutException(OctaviaException):
    message = _('Waiting for compute id %(id)s to go active timeout.')


class InvalidTopology(OctaviaException):
    message = _('Invalid topology specified: %(topology)s')


# L7 policy and rule exceptions
class InvalidL7PolicyAction(APIException):
    msg = _('Invalid L7 Policy action specified: %(action)s')
    code = 400


class InvalidL7PolicyArgs(APIException):
    msg = _('Invalid L7 Policy arguments: %(msg)s')
    code = 400


class InvalidURL(OctaviaException):
    message = _('Not a valid URL: %(url)s')


class InvalidURLPath(APIException):
    msg = _('Not a valid URLPath: %(url_path)s')
    code = 400


class InvalidString(OctaviaException):
    message = _('Invalid characters in %(what)s')


class InvalidRegex(OctaviaException):
    message = _('Unable to parse regular expression: %(e)s')


class InvalidL7Rule(OctaviaException):
    message = _('Invalid L7 Rule: %(msg)s')


class ServerGroupObjectCreateException(OctaviaException):
    message = _('Failed to create server group object.')


class ServerGroupObjectDeleteException(OctaviaException):
    message = _('Failed to delete server group object.')


class InvalidAmphoraOperatingSystem(OctaviaException):
    message = _('Invalid amphora operating system: %(os_name)s')


class QuotaException(APIException):
    msg = _('Quota has been met for resources: %(resource)s')
    code = 403


class ProjectBusyException(APIException):
    msg = _('Project busy.  Unable to lock the project.  Please try again.')
    code = 503


class MissingProjectID(OctaviaException):
    message = _('Missing project ID in request where one is required.')


class MissingAPIProjectID(APIException):
    message = _('Missing project ID in request where one is required.')
    code = 400


class InvalidSubresource(APIException):
    msg = _('%(resource)s %(id)s not found.')
    code = 400


class ValidationException(APIException):
    msg = _('Validation failure: %(detail)s')
    code = 400


class VIPValidationException(APIException):
    msg = _('Validation failure: VIP must contain one of: %(objects)s.')
    code = 400


class InvalidSortKey(APIException):
    msg = _("Supplied sort key '%(key)s' is not valid.")
    code = 400


class InvalidSortDirection(APIException):
    msg = _("Supplied sort direction '%(key)s' is not valid.")
    code = 400


class InvalidMarker(APIException):
    msg = _("Supplied pagination marker '%(key)s' is not valid.")
    code = 400


class InvalidLimit(APIException):
    msg = _("Supplied pagination limit '%(key)s' is not valid.")
    code = 400


class MissingVIPSecurityGroup(OctaviaException):
    message = _('VIP security group is missing for load balancer: %(lb_id)s')


class ProviderNotEnabled(APIException):
    msg = _("Provider '%(prov)s' is not enabled.")
    code = 400


class ProviderNotFound(APIException):
    msg = _("Provider '%(prov)s' was not found.")
    code = 501


class ProviderDriverError(APIException):
    msg = _("Provider '%(prov)s' reports error: %(user_msg)s")
    code = 500


class ProviderNotImplementedError(APIException):
    msg = _("Provider '%(prov)s' does not support a requested action: "
            "%(user_msg)s")
    code = 501


class ProviderUnsupportedOptionError(APIException):
    msg = _("Provider '%(prov)s' does not support a requested option: "
            "%(user_msg)s")
    code = 501
