# Copyright (c) 2018 NEC, Corp.
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

import sys

from oslo_config import cfg
from oslo_upgradecheck import common_checks
from oslo_upgradecheck import upgradecheck
from stevedore import driver as stevedore_driver

# Need to import to load config
from octavia.common import config  # noqa: F401 pylint: disable=unused-import
from octavia.common import constants
from octavia.common import policy
from octavia.controller.worker.v2 import taskflow_jobboard_driver as tsk_driver
from octavia.i18n import _

CONF = cfg.CONF


class Checks(upgradecheck.UpgradeCommands):

    """Contains upgrade checks

    Various upgrade checks should be added as separate methods in this class
    and added to _upgrade_checks tuple.
    """

    def _check_persistence(self):
        try:
            pers_driver = tsk_driver.MysqlPersistenceDriver()
            with pers_driver.get_persistence() as pers:
                if pers.engine.dialect.name == 'sqlite':
                    return upgradecheck.Result(
                        upgradecheck.Code.WARNING,
                        _('Persistence database is using sqlite backend. '
                          'Verification required if persistence_connecton URL '
                          'has been set properly.'))
                return pers
        except Exception:
            return upgradecheck.Result(upgradecheck.Code.FAILURE,
                                       _('Failed to connect to persistence '
                                         'backend for AmphoraV2 provider.'))

    def _check_jobboard(self, persistence):
        try:
            jobboard_driver = stevedore_driver.DriverManager(
                namespace='octavia.worker.jobboard_driver',
                name=CONF.task_flow.jobboard_backend_driver,
                invoke_args=(persistence,),
                invoke_on_load=True).driver
            with jobboard_driver.job_board(persistence) as jb:
                if jb.connected:
                    return upgradecheck.Result(
                        upgradecheck.Code.SUCCESS,
                        _('Persistence database and Jobboard backend for '
                          'AmphoraV2 provider configured.'))
        except Exception:
            # Return FAILURE later
            pass

        return upgradecheck.Result(
            upgradecheck.Code.FAILURE,
            _('Failed to connect to jobboard backend for AmphoraV2 provider. '
              'Check jobboard configuration options in task_flow config '
              'section.'))

    def _check_amphorav2(self):
        default_provider_driver = CONF.api_settings.default_provider_driver
        enabled_provider_drivers = CONF.api_settings.enabled_provider_drivers
        if (default_provider_driver == constants.AMPHORAV2 or
                constants.AMPHORAV2 in enabled_provider_drivers):
            persistence = self._check_persistence()
            if isinstance(persistence, upgradecheck.Result):
                return persistence
            return self._check_jobboard(persistence)
        return upgradecheck.Result(upgradecheck.Code.SUCCESS,
                                   _('AmphoraV2 provider is not enabled.'))

    def _check_yaml_policy(self):
        if CONF.oslo_policy.policy_file.lower().endswith('yaml'):
            return upgradecheck.Result(upgradecheck.Code.SUCCESS,
                                       _('The [oslo_policy] policy_file '
                                         'setting is configured for YAML '
                                         'policy file format.'))
        if CONF.oslo_policy.policy_file.lower().endswith('json'):
            return upgradecheck.Result(
                upgradecheck.Code.WARNING,
                _('The [oslo_policy] policy_file setting is configured for '
                  'JSON policy file format. JSON format policy files have '
                  'been deprecated by oslo policy. Please use the oslo policy '
                  'tool to convert your policy file to YAML format. See this '
                  'patch for more information: '
                  'https://review.opendev.org/733650'))
        return upgradecheck.Result(upgradecheck.Code.FAILURE,
                                   _('Unable to determine the [oslo_policy] '
                                     'policy_file setting file format. '
                                     'Please make sure your policy file is '
                                     'in YAML format and has the suffix of '
                                     '.yaml for the filename. Oslo policy '
                                     'has deprecated the JSON file format.'))

    _upgrade_checks = (
        (_('AmphoraV2 Check'), _check_amphorav2),
        (_('YAML Policy File'), _check_yaml_policy),
        (_('Policy File JSON to YAML Migration'),
         (common_checks.check_policy_json, {'conf': CONF})),
    )


def main():
    policy.Policy()
    return upgradecheck.main(
        CONF, project='octavia', upgrade_command=Checks())


if __name__ == '__main__':
    sys.exit(main())
