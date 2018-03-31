# Copyright 2018 Rackspace, US Inc.
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

from octavia.i18n import _


class DriverError(Exception):
    """Catch all exception that drivers can raise.

    This exception includes two strings: The user fault string and the
    optional operator fault string. The user fault string,
    "user_fault_string", will be provided to the API requester. The operator
    fault string, "operator_fault_string",  will be logged in the Octavia API
    log file for the operator to use when debugging.

    :param user_fault_string: String provided to the API requester.
    :type user_fault_string: string
    :param operator_fault_string: Optional string logged by the Octavia API
      for the operator to use when debugging.
    :type operator_fault_string: string
    """
    user_fault_string = _("An unknown driver error occurred.")
    operator_fault_string = _("An unknown driver error occurred.")

    def __init__(self, *args, **kwargs):
        self.user_fault_string = kwargs.pop('user_fault_string',
                                            self.user_fault_string)
        self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                self.operator_fault_string)
        super(DriverError, self).__init__(*args, **kwargs)


class NotImplementedError(Exception):
    """Exception raised when a driver does not implement an API function.

    :param user_fault_string: String provided to the API requester.
    :type user_fault_string: string
    :param operator_fault_string: Optional string logged by the Octavia API
      for the operator to use when debugging.
    :type operator_fault_string: string
    """
    user_fault_string = _("This feature is not implemented by the provider.")
    operator_fault_string = _("This feature is not implemented by this "
                              "provider.")

    def __init__(self, *args, **kwargs):
        self.user_fault_string = kwargs.pop('user_fault_string',
                                            self.user_fault_string)
        self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                self.operator_fault_string)
        super(NotImplementedError, self).__init__(*args, **kwargs)


class UnsupportedOptionError(Exception):
    """Exception raised when a driver does not support an option.

    Provider drivers will validate that they can complete the request -- that
    all options are supported by the driver. If the request fails validation,
    drivers will raise an UnsupportedOptionError exception. For example, if a
    driver does not support a flavor passed as an option to load balancer
    create(), the driver will raise an UnsupportedOptionError and include a
    message parameter providing an explanation of the failure.

    :param user_fault_string: String provided to the API requester.
    :type user_fault_string: string
    :param operator_fault_string: Optional string logged by the Octavia API
      for the operator to use when debugging.
    :type operator_fault_string: string
    """
    user_fault_string = _("A specified option is not supported by this "
                          "provider.")
    operator_fault_string = _("A specified option is not supported by this "
                              "provider.")

    def __init__(self, *args, **kwargs):
        self.user_fault_string = kwargs.pop('user_fault_string',
                                            self.user_fault_string)
        self.operator_fault_string = kwargs.pop('operator_fault_string',
                                                self.operator_fault_string)
        super(UnsupportedOptionError, self).__init__(*args, **kwargs)
