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

"""Test of Policy Engine For Octavia."""

import logging
import tempfile

from oslo_config import fixture as oslo_fixture
from oslo_policy import policy as oslo_policy
import requests_mock

from octavia.common import config
from octavia.common import context
from octavia.common import exceptions
from octavia.common import policy
from octavia.tests.unit import base

CONF = config.cfg.CONF
LOG = logging.getLogger(__name__)


class PolicyFileTestCase(base.TestCase):

    def setUp(self):
        super(PolicyFileTestCase, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config(CONF))
        policy.reset()
        self.target = {}

    def test_modified_policy_reloads(self):
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as tmp:
            self.conf.load_raw_values(
                group='oslo_policy', policy_file=tmp.name)

            tmp.write('{"example:test": ""}')
            tmp.flush()

            self.context = context.Context('fake', 'fake')

            rule = oslo_policy.RuleDefault('example:test', "")
            policy.get_enforcer().register_defaults([rule])

            action = "example:test"
            policy.get_enforcer().authorize(action, self.target, self.context)

            tmp.seek(0)
            tmp.write('{"example:test": "!"}')
            tmp.flush()
            policy.get_enforcer().load_rules(True)
            self.assertRaises(exceptions.PolicyForbidden,
                              policy.get_enforcer().authorize,
                              action, self.target, self.context)


class PolicyTestCase(base.TestCase):

    def setUp(self):
        super(PolicyTestCase, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config())
        # diltram: this one must be removed after fixing issue in oslo.config
        # https://bugs.launchpad.net/oslo.config/+bug/1645868
        self.conf.conf.__call__(args=[])
        policy.reset()
        self.context = context.Context('fake', 'fake', roles=['member'])

        self.rules = [
            oslo_policy.RuleDefault("true", "@"),
            oslo_policy.RuleDefault("example:allowed", "@"),
            oslo_policy.RuleDefault("example:denied", "!"),
            oslo_policy.RuleDefault("example:get_http",
                                    "http://www.example.com"),
            oslo_policy.RuleDefault("example:my_file",
                                    "role:compute_admin or "
                                    "project_id:%(project_id)s"),
            oslo_policy.RuleDefault("example:early_and_fail", "! and @"),
            oslo_policy.RuleDefault("example:early_or_success", "@ or !"),
            oslo_policy.RuleDefault("example:lowercase_admin",
                                    "role:admin or role:sysadmin"),
            oslo_policy.RuleDefault("example:uppercase_admin",
                                    "role:ADMIN or role:sysadmin"),
        ]
        policy.get_enforcer().register_defaults(self.rules)
        self.target = {}

    def test_authorize_nonexistent_action_throws(self):
        action = "example:noexist"
        self.assertRaises(
            oslo_policy.PolicyNotRegistered, policy.get_enforcer().authorize,
            action, self.target, self.context)

    def test_authorize_bad_action_throws(self):
        action = "example:denied"
        self.assertRaises(
            exceptions.PolicyForbidden, policy.get_enforcer().authorize,
            action, self.target, self.context)

    def test_authorize_bad_action_noraise(self):
        action = "example:denied"
        result = policy.get_enforcer().authorize(action, self.target,
                                                 self.context, False)
        self.assertFalse(result)

    def test_authorize_good_action(self):
        action = "example:allowed"
        result = policy.get_enforcer().authorize(action, self.target,
                                                 self.context)
        self.assertTrue(result)

    @requests_mock.mock()
    def test_authorize_http(self, req_mock):
        req_mock.post('http://www.example.com/', text='False')
        action = "example:get_http"
        self.assertRaises(exceptions.PolicyForbidden,
                          policy.get_enforcer().authorize, action, self.target,
                          self.context)

    def test_templatized_authorization(self):
        target_mine = {'project_id': 'fake'}
        target_not_mine = {'project_id': 'another'}
        action = "example:my_file"

        policy.get_enforcer().authorize(action, target_mine, self.context)
        self.assertRaises(exceptions.PolicyForbidden,
                          policy.get_enforcer().authorize,
                          action, target_not_mine, self.context)

    def test_early_AND_authorization(self):
        action = "example:early_and_fail"
        self.assertRaises(exceptions.PolicyForbidden,
                          policy.get_enforcer().authorize, action, self.target,
                          self.context)

    def test_early_OR_authorization(self):
        action = "example:early_or_success"
        policy.get_enforcer().authorize(action, self.target, self.context)

    def test_ignore_case_role_check(self):
        lowercase_action = "example:lowercase_admin"
        uppercase_action = "example:uppercase_admin"

        # NOTE(dprince) we mix case in the Admin role here to ensure
        # case is ignored
        self.context = context.Context('admin', 'fake', roles=['AdMiN'])

        policy.get_enforcer().authorize(lowercase_action, self.target,
                                        self.context)
        policy.get_enforcer().authorize(uppercase_action, self.target,
                                        self.context)

    def test_check_is_admin_fail(self):
        self.assertFalse(policy.get_enforcer().check_is_admin(self.context))

    def test_check_is_admin(self):
        self.context = context.Context('admin', 'fake', roles=['AdMiN'])

        self.assertTrue(policy.get_enforcer().check_is_admin(self.context))

    def test_get_enforcer(self):
        self.assertTrue(isinstance(policy.get_no_context_enforcer(),
                                   oslo_policy.Enforcer))


class IsAdminCheckTestCase(base.TestCase):

    def setUp(self):
        super(IsAdminCheckTestCase, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config())
        # diltram: this one must be removed after fixing issue in oslo.config
        # https://bugs.launchpad.net/oslo.config/+bug/1645868
        self.conf.conf.__call__(args=[])

        self.context = context.Context('fake', 'fake')

    def test_init_true(self):
        check = policy.IsAdminCheck('is_admin', 'True')

        self.assertEqual(check.kind, 'is_admin')
        self.assertEqual(check.match, 'True')
        self.assertTrue(check.expected)

    def test_init_false(self):
        check = policy.IsAdminCheck('is_admin', 'nottrue')

        self.assertEqual(check.kind, 'is_admin')
        self.assertEqual(check.match, 'False')
        self.assertFalse(check.expected)

    def test_call_true(self):
        check = policy.IsAdminCheck('is_admin', 'True')

        self.assertTrue(
            check('target', dict(is_admin=True), policy.get_enforcer()))
        self.assertFalse(
            check('target', dict(is_admin=False), policy.get_enforcer()))

    def test_call_false(self):
        check = policy.IsAdminCheck('is_admin', 'False')

        self.assertFalse(
            check('target', dict(is_admin=True), policy.get_enforcer()))
        self.assertTrue(
            check('target', dict(is_admin=False), policy.get_enforcer()))


class AdminRolePolicyTestCase(base.TestCase):

    def setUp(self):
        super(AdminRolePolicyTestCase, self).setUp()

        self.conf = self.useFixture(oslo_fixture.Config())
        # diltram: this one must be removed after fixing issue in oslo.config
        # https://bugs.launchpad.net/oslo.config/+bug/1645868
        self.conf.conf.__call__(args=[])

        self.context = context.Context('fake', 'fake', roles=['member'])
        self.actions = policy.get_enforcer().get_rules().keys()
        self.target = {}

    def test_authorize_admin_actions_with_nonadmin_context_throws(self):
        """Check if non-admin context passed to admin actions throws

           Policy not authorized exception
        """
        for action in self.actions:
            self.assertRaises(
                exceptions.PolicyForbidden, policy.get_enforcer().authorize,
                action, self.target, self.context)
