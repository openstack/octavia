# Copyright 2016 IBM Corp.
# Copyright 2017 Rackspace, US Inc.
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

from taskflow.patterns import linear_flow
from taskflow import task

from oslo_log import log as logging
from oslo_utils import uuidutils

from octavia.distributor.drivers import driver_base

LOG = logging.getLogger(__name__)


class NoopProvidesRequiresTask(task.Task):
    def __init__(self, name, provides_dicts=None, requires=None):
        if provides_dicts is None:
            provides_dicts = {}
        super(NoopProvidesRequiresTask, self).__init__(
            name=name,
            provides=list(provides_dicts),
            requires=requires)
        self.provides_dict = provides_dicts

    def execute(self, *args, **kwargs):
        return self.provides_dict.values()


class NoopManager(object):
    def __init__(self):
        super(NoopManager, self).__init__()

    def get_create_distributor_subflow(self):
        LOG.debug('Distributor %s create_distributor', self.__class__.__name__)
        create_distributor_flow = linear_flow.Flow('create-distributor')
        create_distributor_flow.add(NoopProvidesRequiresTask(
            'create-distributor-task',
            requires=('load_balancer'),
            provides_dicts={'distributor_id': uuidutils.generate_uuid()}))
        return create_distributor_flow

    def get_delete_distributor_subflow(self):
        LOG.debug('Distributor %s delete_distributor', self.__class__.__name__)
        delete_distributor_flow = linear_flow.Flow('delete-distributor')
        delete_distributor_flow.add(NoopProvidesRequiresTask(
            'delete-distributor-task', requires=('distributor_id')))
        return delete_distributor_flow

    def get_add_vip_subflow(self):
        LOG.debug('Distributor %s add_vip', self.__class__.__name__)
        add_vip_flow = linear_flow.Flow('add-vip')
        add_vip_flow.add(NoopProvidesRequiresTask(
            'add-vip-task', requires=('distributor_id', 'vip',
                                      'vip_alg', 'vip_persistence')))
        return add_vip_flow

    def get_remove_vip_subflow(self):
        LOG.debug('Distributor %s remove_vip', self.__class__.__name__)
        remove_vip_flow = linear_flow.Flow('remove-vip')
        remove_vip_flow.add(NoopProvidesRequiresTask('remove-vip-task',
                            requires=('distributor_id', 'vip')))
        return remove_vip_flow

    def get_register_amphorae_subflow(self):
        LOG.debug('Distributor %s register_amphorae', self.__class__.__name__)
        register_amphorae_flow = linear_flow.Flow('register_amphorae')
        register_amphorae_flow.add(NoopProvidesRequiresTask(
            'register_amphorae_task', requires=('distributor_id', 'amphorae')))
        return register_amphorae_flow

    def get_drain_amphorae_subflow(self):
        LOG.debug('Distributor %s drain_amphorae', self.__class__.__name__)
        drain_amphorae_flow = linear_flow.Flow('drain-amphorae')
        drain_amphorae_flow.add(NoopProvidesRequiresTask(
            'drain_amphorae_task', requires=('distributor_id', 'amphorae')))
        return drain_amphorae_flow

    def get_unregister_amphorae_subflow(self):
        LOG.debug('Distributor %s unregister_amphorae',
                  self.__class__.__name__)
        unregister_amphorae_flow = linear_flow.Flow('unregister_amphora')
        unregister_amphorae_flow.add(NoopProvidesRequiresTask(
            'unregister_amphorae_task', requires=('distributor_id',
                                                  'amphorae')))
        return unregister_amphorae_flow


class NoopDistributorDriver(driver_base.DistributorDriver):
    def __init__(self):
        super(NoopDistributorDriver, self).__init__()
        self.driver = NoopManager()

    def get_create_distributor_subflow(self):
        return self.driver.get_create_distributor_subflow()

    def get_delete_distributor_subflow(self):
        return self.driver.get_delete_distributor_subflow()

    def get_add_vip_subflow(self):
        return self.driver.get_add_vip_subflow()

    def get_remove_vip_subflow(self):
        return self.driver.get_remove_vip_subflow()

    def get_register_amphorae_subflow(self):
        return self.driver.get_register_amphorae_subflow()

    def get_drain_amphorae_subflow(self):
        self.driver.get_drain_amphorae_subflow()

    def get_unregister_amphorae_subflow(self):
        self.driver.get_unregister_amphorae_subflow()
