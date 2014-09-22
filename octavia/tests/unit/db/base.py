#    Copyright 2014 Rackspace
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

from oslo.db.sqlalchemy import test_base

from octavia.common import constants
from octavia.db import base_models
from octavia.db import models


class OctaviaDBTestBase(test_base.DbTestCase):

    def setUp(self):
        super(OctaviaDBTestBase, self).setUp()
        # needed for closure
        engine = self.engine
        base_models.BASE.metadata.create_all(bind=engine)
        self._seed_lookup_tables()

        def unregister_models():
            """Unregister all data models."""
            base_models.BASE.metadata.drop_all(bind=engine)

        self.addCleanup(unregister_models)

        self.session = self._get_session()

    def _get_session(self):
        return self.sessionmaker(bind=self.engine, expire_on_commit=True)

    def _seed_lookup_tables(self):
        session = self._get_session()
        self._seed_lookup_table(
            session, constants.SUPPORTED_PROVISIONING_STATUSES,
            models.ProvisioningStatus)
        self._seed_lookup_table(
            session, constants.SUPPORTED_HEALTH_MONITOR_TYPES,
            models.HealthMonitorType)
        self._seed_lookup_table(
            session, constants.SUPPORTED_LB_ALGORITHMS,
            models.Algorithm)
        self._seed_lookup_table(
            session, constants.SUPPORTED_PROTOCOLS,
            models.Protocol)
        self._seed_lookup_table(
            session, constants.SUPPORTED_OPERATING_STATUSES,
            models.OperatingStatus)
        self._seed_lookup_table(
            session, constants.SUPPORTED_SP_TYPES,
            models.SessionPersistenceType)

    def _seed_lookup_table(self, session, name_list, model_cls):
        for name in name_list:
            with session.begin():
                model = model_cls(name=name)
                session.add(model)