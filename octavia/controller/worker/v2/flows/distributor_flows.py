# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""TaskFlow orchestration for active-active distributors."""

from oslo_config import cfg
from stevedore import driver as stevedore_driver
from taskflow.patterns import linear_flow

from octavia.common import constants
from octavia.controller.worker.v2.tasks import database_tasks
from octavia.controller.worker.v2.tasks import compute_tasks
from octavia.controller.worker.v2.tasks import distributor_tasks
from octavia.controller.worker.v2.tasks import network_tasks
from octavia.controller.worker.v2.tasks import cert_task

CONF = cfg.CONF


class DistributorFlows:
    def __init__(self):
        self.driver = stevedore_driver.DriverManager(
            namespace='octavia.distributor.drivers',
            name=CONF.controller_worker.distributor_driver,
            invoke_on_load=True).driver

    def get_create_distributor_flow(self):
        """Create and bind the distributor to the real LB VIP port.

        OVN's floating-IP NAT resolves the VIP to the Octavia VIP logical
        port.  Binding that port to the distributor gives the NAT path a
        concrete Nova interface; active amphora VIP address-pairs are added
        only afterward by the active-active amphora flow.
        """
        flow = linear_flow.Flow(constants.CREATE_DISTRIBUTOR_FLOW)
        flow.add(distributor_tasks.GenerateDistributorId(
            provides=constants.DISTRIBUTOR_ID))
        flow.add(self.driver.get_create_distributor_subflow())
        flow.add(network_tasks.CreateDistributorFrontendPort(
            requires=(constants.LOADBALANCER, constants.VIP,
                      constants.DISTRIBUTOR_ID),
            provides=constants.DISTRIBUTOR_PORT))
        flow.add(cert_task.GenerateServerPEMTask(
            rebind={'amphora_id': constants.DISTRIBUTOR_ID},
            provides=constants.DISTRIBUTOR_SERVER_PEM))
        flow.add(compute_tasks.DistributorComputeCreate(
            rebind={'distributor_id': constants.DISTRIBUTOR_ID,
                    'server_pem': constants.DISTRIBUTOR_SERVER_PEM,
                    'distributor_port': constants.DISTRIBUTOR_PORT},
            provides=constants.DISTRIBUTOR_COMPUTE_ID))
        wait_flow = linear_flow.Flow(
            'wait-for-distributor', retry=compute_tasks.ComputeRetry())
        wait_flow.add(compute_tasks.DistributorComputeWait(
            rebind={'compute_id': constants.DISTRIBUTOR_COMPUTE_ID},
            provides=constants.DISTRIBUTOR_COMPUTE))
        flow.add(wait_flow)
        flow.add(distributor_tasks.CreateDistributorInDB(
            requires=(constants.DISTRIBUTOR_ID,
                      constants.LOADBALANCER,
                      constants.DISTRIBUTOR_COMPUTE,
                      constants.DISTRIBUTOR_PORT)))
        flow.add(distributor_tasks.AssociateDistributorInDB(
            requires=(constants.DISTRIBUTOR_ID,
                      constants.LOADBALANCER)))
        flow.add(distributor_tasks.WaitForDistributorAgent(
            self.driver, requires=constants.DISTRIBUTOR_ID))
        flow.add(self.driver.get_add_vip_subflow())
        return flow

    def get_delete_distributor_flow(self):
        flow = linear_flow.Flow(constants.DELETE_DISTRIBUTOR_FLOW)
        flow.add(distributor_tasks.GetDistributorIDFromLoadbalancer(
            requires=constants.LOADBALANCER,
            provides=constants.DISTRIBUTOR_ID))
        flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORAE))
        flow.add(self.driver.get_unregister_amphorae_subflow())
        flow.add(self.driver.get_remove_vip_subflow())
        flow.add(self.driver.get_delete_distributor_subflow())
        flow.add(distributor_tasks.DeleteDistributorCompute(
            requires=constants.DISTRIBUTOR_ID))
        flow.add(network_tasks.ReleaseDistributorFrontendPort(
            requires=constants.DISTRIBUTOR_ID))
        flow.add(distributor_tasks.MarkDistributorDeletedInDB(
            requires=constants.DISTRIBUTOR_ID))
        return flow

    def get_register_amphorae_flow(self):
        flow = linear_flow.Flow(constants.REGISTER_AMPHORAE_FLOW)
        flow.add(database_tasks.GetAmphoraeFromLoadbalancer(
            requires=constants.LOADBALANCER_ID,
            provides=constants.AMPHORAE))
        flow.add(self.driver.get_register_amphorae_subflow())
        return flow

    def get_unregister_amphorae_flow(self):
        flow = linear_flow.Flow(constants.UNREGISTER_AMPHORAE_FLOW)
        flow.add(self.driver.get_unregister_amphorae_subflow())
        return flow

    def get_unregister_amphora_flow(self, amphora):
        flow = linear_flow.Flow(constants.UNREGISTER_AMPHORAE_FLOW + '-one')
        flow.add(distributor_tasks.DistributorUnregisterAmphora(
            self.driver,
            requires=(constants.DISTRIBUTOR_ID, constants.LOADBALANCER,
                      constants.AMPHORA),
            inject={constants.AMPHORA: amphora}))
        return flow
