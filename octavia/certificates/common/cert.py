# Copyright (c) 2014 The Johns Hopkins University/Applied Physics Laboratory
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

import abc

import six


@six.add_metaclass(abc.ABCMeta)
class Cert(object):
    """Base class to represent all certificates."""

    @abc.abstractmethod
    def get_certificate(self):
        """Returns the certificate."""
        pass

    @abc.abstractmethod
    def get_intermediates(self):
        """Returns the intermediate certificates."""
        pass

    @abc.abstractmethod
    def get_private_key(self):
        """Returns the private key for the certificate."""
        pass

    @abc.abstractmethod
    def get_private_key_passphrase(self):
        """Returns the passphrase for the private key."""
        pass
