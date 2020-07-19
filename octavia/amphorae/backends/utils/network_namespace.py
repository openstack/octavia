# Copyright 2020 Red Hat, Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import ctypes
import os


class NetworkNamespace(object):
    """A network namespace context manager.

    Runs wrapped code inside the specified network namespace.

    :param netns: The network namespace name to enter.
    """
    # from linux/sched.h - We want to enter a network namespace
    CLONE_NEWNET = 0x40000000

    @staticmethod
    def _error_handler(result, func, arguments):
        if result == -1:
            errno = ctypes.get_errno()
            raise OSError(errno, os.strerror(errno))

    def __init__(self, netns):
        self.current_netns = '/proc/{pid}/ns/net'.format(pid=os.getpid())
        self.target_netns = '/var/run/netns/{netns}'.format(netns=netns)
        # reference: man setns(2)
        self.set_netns = ctypes.CDLL('libc.so.6', use_errno=True).setns
        self.set_netns.errcheck = self._error_handler

    def __enter__(self):
        # Save the current network namespace
        self.current_netns_fd = open(self.current_netns)
        with open(self.target_netns) as fd:
            self.set_netns(fd.fileno(), self.CLONE_NEWNET)

    def __exit__(self, *args):
        # Return to the previous network namespace
        self.set_netns(self.current_netns_fd.fileno(), self.CLONE_NEWNET)
        self.current_netns_fd.close()
