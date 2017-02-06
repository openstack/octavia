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

from oslo_config import fixture as oslo_fixture
from oslo_db.sqlalchemy import test_base

from octavia.common import config
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import base_models
from octavia.db import models


class OctaviaDBTestBase(test_base.DbTestCase):

    def setUp(self):
        super(OctaviaDBTestBase, self).setUp()
        # NOTE(blogan): doing this for now because using the engine and
        # session set up in the fixture for test_base.DbTestCase does not work
        # with the API functional tests.  Need to investigate more if this
        # becomes a problem
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))
        conf.config(group="database", connection='sqlite://')

        # needed for closure
        engine = db_api.get_engine()
        session = db_api.get_session()
        base_models.BASE.metadata.create_all(engine)
        self._seed_lookup_tables(session)

        def clear_tables():
            """Unregister all data models."""
            base_models.BASE.metadata.drop_all(engine)

        self.addCleanup(clear_tables)

        self.session = session

    def _seed_lookup_tables(self, session):
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
        self._seed_lookup_table(session, constants.SUPPORTED_AMPHORA_ROLES,
                                models.AmphoraRoles)
        self._seed_lookup_table(session, constants.SUPPORTED_LB_TOPOLOGIES,
                                models.LBTopology)
        self._seed_lookup_table(session, constants.SUPPORTED_VRRP_AUTH,
                                models.VRRPAuthMethod)
        self._seed_lookup_table(session, constants.SUPPORTED_L7RULE_TYPES,
                                models.L7RuleType)
        self._seed_lookup_table(session,
                                constants.SUPPORTED_L7RULE_COMPARE_TYPES,
                                models.L7RuleCompareType)
        self._seed_lookup_table(session, constants.SUPPORTED_L7POLICY_ACTIONS,
                                models.L7PolicyAction)

    def _seed_lookup_table(self, session, name_list, model_cls):
        for name in name_list:
            with session.begin():
                model = model_cls(name=name)
                session.add(model)
