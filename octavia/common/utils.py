# Copyright 2011, VMware, Inc., 2014 A10 Networks
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
#
# Borrowed from nova code base, more utilities will be added/borrowed as and
# when needed.

"""Utilities and helper functions."""

import datetime
import hashlib
import random
import socket


from oslo_log import log as logging
from oslo_utils import excutils

LOG = logging.getLogger(__name__)


def get_hostname():
    return socket.gethostname()


def get_random_string(length):
    """Get a random hex string of the specified length.

    based on Cinder library
      cinder/transfer/api.py
    """
    rndstr = ""
    random.seed(datetime.datetime.now().microsecond)
    while len(rndstr) < length:
        rndstr += hashlib.sha224(
            str(random.random()).encode('ascii')
        ).hexdigest()

    return rndstr[0:length]


class exception_logger(object):
    """Wrap a function and log raised exception

    :param logger: the logger to log the exception default is LOG.exception

    :returns: origin value if no exception raised; re-raise the exception if
              any occurred

    """
    def __init__(self, logger=None):
        self.logger = logger

    def __call__(self, func):
        if self.logger is None:
            LOG = logging.getLogger(func.__module__)
            self.logger = LOG.exception

        def call(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                with excutils.save_and_reraise_exception():
                    self.logger(e)
        return call
