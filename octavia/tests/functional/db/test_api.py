#    Copyright 2026 Red Hat
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

import threading

from octavia.db import api as db_api
from octavia.tests.functional.db import base


class TestDBAPI(base.OctaviaDBTestBase):

    def test_wait_for_connection_success(self):
        exit_event = threading.Event()

        # This should complete successfully without blocking
        db_api.wait_for_connection(exit_event)

        # Verify we can still execute queries after wait_for_connection
        with db_api.get_engine().connect() as conn:
            result = conn.execute(db_api.select(1))
            self.assertIsNotNone(result)
