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

import os

from oslo_config import cfg
from oslo_config import fixture as oslo_fixture
from oslo_db.sqlalchemy import session as db_session
from oslotest import base as test_base

from octavia.common import config
from octavia.common import constants
from octavia.db import api as db_api
from octavia.db import base_models
from octavia.db import models

from octavia.tests import fixtures as oc_fixtures


class OctaviaDBTestBase(test_base.BaseTestCase):

    def setUp(self, connection_string='sqlite://'):
        super().setUp()

        self.connection_string = connection_string
        self.warning_fixture = self.useFixture(oc_fixtures.WarningsFixture())

        # NOTE(blogan): doing this for now because using the engine and
        # session set up in the fixture for test_base.DbTestCase does not work
        # with the API functional tests.  Need to investigate more if this
        # becomes a problem
        conf = self.useFixture(oslo_fixture.Config(config.cfg.CONF))
        conf.config(group="database", connection=connection_string)

        # Disable pool_timeout when using sqlite with a file
        # pool_timeout is not support by sqlalchemy 2 with SQLite/NullPool
        if connection_string.startswith('sqlite:///'):
            conf.config(group="database", pool_timeout=None)

        engine, self.session = self._get_db_engine_session()

        base_models.BASE.metadata.create_all(engine)

        with self.session.begin():
            self._seed_lookup_tables(self.session)

        def clear_tables():
            """Unregister all data models."""
            base_models.BASE.metadata.drop_all(engine)
            # If we created a file, clean it up too
            if 'sqlite:///' in connection_string:
                os.remove(connection_string.replace('sqlite:///', ''))

        self.addCleanup(clear_tables)

    def _get_db_engine_session(self):
        # We need to get our own Facade so that the file backed sqlite tests
        # don't use the _FACADE singleton. Some tests will use in-memory
        # sqlite, some will use a file backed sqlite.
        if 'sqlite:///' in self.connection_string:
            facade = db_session.EngineFacade.from_config(cfg.CONF,
                                                         sqlite_fk=True)
            engine = facade.get_engine()
            session = facade.get_session(expire_on_commit=True)
        else:
            engine = db_api.get_engine()
            session = db_api.get_session()
        return engine, session

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
        self._seed_lookup_table(session, constants.SUPPORTED_CLIENT_AUTH_MODES,
                                models.ClientAuthenticationMode)
        # Add in the id='DELETED' placeholders
        deleted_flavor_profile = models.FlavorProfile(
            id=constants.NIL_UUID, name='DELETED-PLACEHOLDER',
            provider_name=constants.DELETED, flavor_data='{}')
        session.add(deleted_flavor_profile)
        session.flush()
        deleted_flavor = models.Flavor(
            id=constants.NIL_UUID, flavor_profile_id=constants.NIL_UUID,
            name='DELETED-PLACEHOLDER', enabled=False,
            description='Placeholder for DELETED LBs with DELETED flavors')
        session.add(deleted_flavor)
        session.flush()
        deleted_az_profile = models.AvailabilityZoneProfile(
            id=constants.NIL_UUID, name='DELETED-PLACEHOLDER',
            provider_name=constants.DELETED, availability_zone_data='{}')
        session.add(deleted_az_profile)
        session.flush()
        deleted_az = models.AvailabilityZone(
            availability_zone_profile_id=constants.NIL_UUID,
            name=constants.NIL_UUID, enabled=False,
            description='Placeholder for DELETED LBs with DELETED '
                        'availability zones')
        session.add(deleted_az)
        session.flush()

    def _seed_lookup_table(self, session, name_list, model_cls):
        for name in name_list:
            model = model_cls(name=name)
            session.add(model)
