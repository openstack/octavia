# Copyright (c) 2016 Hewlett Packard Enterprise Development Company LP
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

import fixtures
import mock


# Borrowed from neutron
# https://review.opendev.org/#/c/232716/
class OpenFixture(fixtures.Fixture):
    """Mock access to a specific file while preserving open for others."""

    def __init__(self, filepath, contents=''):
        self.path = filepath
        self.contents = contents

    def _setUp(self):
        self.mock_open = mock.mock_open(read_data=self.contents)
        # work around for https://bugs.python.org/issue21258
        self.mock_open.return_value.__iter__ = (
            lambda self: iter(self.readline, ''))
        self._orig_open = open

        def replacement_open(name, *args, **kwargs):
            if name == self.path:
                return self.mock_open(name, *args, **kwargs)
            return self._orig_open(name, *args, **kwargs)

        self._patch = mock.patch('six.moves.builtins.open',
                                 new=replacement_open)
        self._patch.start()
        self.addCleanup(self._patch.stop)
