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
from oslo_middleware.healthcheck import pluginbase

from octavia.db import api as db_apis
from octavia.db import healthcheck


class OctaviaDBHealthcheck(pluginbase.HealthcheckBaseExtension):

    UNAVAILABLE_REASON = 'The Octavia database is unavailable.'

    def __init__(self, *args, **kwargs):
        super(OctaviaDBHealthcheck, self).__init__(*args, **kwargs)

    def healthcheck(self, server_port):
        try:
            result, message = healthcheck.check_database_connection(
                db_apis.get_session())
            if result:
                return OctaviaDBCheckResult(available=True, reason="OK")
            else:
                return OctaviaDBCheckResult(available=False,
                                            reason=self.UNAVAILABLE_REASON,
                                            details=message)
        except Exception as e:
            return OctaviaDBCheckResult(available=False,
                                        reason=self.UNAVAILABLE_REASON,
                                        details=str(e))


class OctaviaDBCheckResult(pluginbase.HealthcheckResult):
    """Result sub-class to provide a unique name in detail reports."""

    def __init__(self, *args, **kwargs):
        super(OctaviaDBCheckResult, self).__init__(*args, **kwargs)
