# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

from oslo_log import log as logging
from oslo_config import cfg
from oslo_utils import uuidutils
import time
from stevedore import driver as stevedore_driver
from taskflow import task

from octavia.common import constants
from octavia.controller.worker import task_utils
from octavia.db import api as db_api
from octavia.db import repositories as repo

LOG = logging.getLogger(__name__)
CONF = cfg.CONF


class BaseDistributorTask(task.Task):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.distributor_repo = repo.DistributorRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.task_utils = task_utils.TaskUtils()


class CreateDistributorInDB(BaseDistributorTask):
    def execute(self, distributor_id, loadbalancer, distributor_compute,
                distributor_port):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.create(
                session,
                id=distributor_id,
                distributor_driver=CONF.controller_worker.distributor_driver,
                compute_id=distributor_compute[constants.COMPUTE_ID],
                lb_network_ip=distributor_compute[constants.LB_NETWORK_IP],
                frontend_port_id=distributor_port[constants.ID],
                frontend_mac=distributor_port[constants.MAC_ADDRESS],
                topology=constants.TOPOLOGY_ACTIVE_ACTIVE,
                provisioning_status=constants.ACTIVE,
                operating_status=constants.ONLINE)
        LOG.info('Created active-active distributor %s for LB %s',
                 distributor.id, loadbalancer[constants.LOADBALANCER_ID])

    def revert(self, result, distributor_id, *args, **kwargs):
        try:
            session = db_api.get_session()
            with session.begin():
                self.distributor_repo.delete(session, id=distributor_id)
        except Exception:
            LOG.exception('Failed to revert distributor DB row %s',
                          distributor_id)


class DeleteDistributorCompute(BaseDistributorTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.compute = stevedore_driver.DriverManager(
            namespace='octavia.compute.drivers',
            name=CONF.controller_worker.compute_driver,
            invoke_on_load=True).driver

    def execute(self, distributor_id):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
        if distributor and distributor.compute_id:
            self.compute.delete(distributor.compute_id)


class GetDistributorFrontendPortID(BaseDistributorTask):
    def execute(self, distributor_id):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
        return distributor.frontend_port_id if distributor else None


class AssociateDistributorInDB(BaseDistributorTask):
    def execute(self, distributor_id, loadbalancer):
        session = db_api.get_session()
        with session.begin():
            self.loadbalancer_repo.update(
                session, loadbalancer[constants.LOADBALANCER_ID],
                distributor_id=distributor_id)

    def revert(self, result, distributor_id, loadbalancer, *args, **kwargs):
        try:
            session = db_api.get_session()
            with session.begin():
                self.loadbalancer_repo.update(
                    session, loadbalancer[constants.LOADBALANCER_ID],
                    distributor_id=None)
        except Exception:
            LOG.exception('Failed to revert distributor association for LB %s',
                          loadbalancer[constants.LOADBALANCER_ID])


class WaitForDistributorAgent(BaseDistributorTask):
    """Wait for the freshly booted distributor REST agent to answer."""

    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id):
        last_error = None
        for attempt in range(CONF.controller_worker.amp_active_retries):
            session = db_api.get_session()
            with session.begin():
                distributor = self.distributor_repo.get(
                    session, id=distributor_id)
            try:
                info = self.driver.get_info(distributor)
                if info is not None:
                    return info
            except Exception as exc:
                last_error = exc
            if attempt + 1 < CONF.controller_worker.amp_active_retries:
                time.sleep(CONF.controller_worker.amp_active_wait_sec)
        raise RuntimeError('Distributor agent did not become ready: %s' %
                           last_error)


class GetDistributorIDFromLoadbalancer(BaseDistributorTask):
    def execute(self, loadbalancer):
        session = db_api.get_session()
        with session.begin():
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        return lb.distributor_id


class MarkDistributorDeletedInDB(BaseDistributorTask):
    def execute(self, distributor_id):
        session = db_api.get_session()
        with session.begin():
            self.distributor_repo.update(
                session, distributor_id,
                provisioning_status=constants.DELETED)


class GenerateDistributorId(task.Task):
    def execute(self):
        return uuidutils.generate_uuid()


class DistributorAddVIP(BaseDistributorTask):
    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id, loadbalancer, vip):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        self.driver.post_vip_plug(
            distributor, lb, distributor.frontend_mac,
            constants.TOPOLOGY_ACTIVE_ACTIVE,
            CONF.controller_worker.active_active_desired_amphorae)


class DistributorRegisterAmphorae(BaseDistributorTask):
    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id, loadbalancer, amphorae):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for amphora in amphorae:
            if (amphora.get(constants.STATUS) != constants.AMPHORA_ALLOCATED or
                    amphora.get(constants.ROLE) != constants.ROLE_IN_CLUSTER):
                continue
            self.driver.register_amphora(
                distributor, lb, amphora, constants.TOPOLOGY_ACTIVE_ACTIVE,
                CONF.controller_worker.active_active_desired_amphorae)


class DistributorRemoveVIP(BaseDistributorTask):
    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id, loadbalancer):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        self.driver.pre_vip_unplug(distributor, lb)


class DistributorUnregisterAmphorae(BaseDistributorTask):
    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id, loadbalancer, amphorae):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        for amphora in amphorae:
            self.driver.unregister_amphora(
                distributor, lb, amphora, constants.TOPOLOGY_ACTIVE_ACTIVE,
                CONF.controller_worker.active_active_desired_amphorae)


class DistributorUnregisterAmphora(BaseDistributorTask):
    def __init__(self, driver, **kwargs):
        self.driver = driver
        super().__init__(**kwargs)

    def execute(self, distributor_id, loadbalancer, amphora):
        session = db_api.get_session()
        with session.begin():
            distributor = self.distributor_repo.get(session,
                                                    id=distributor_id)
            lb = self.loadbalancer_repo.get(
                session, id=loadbalancer[constants.LOADBALANCER_ID])
        self.driver.unregister_amphora(
            distributor, lb, amphora, constants.TOPOLOGY_ACTIVE_ACTIVE,
            CONF.controller_worker.active_active_desired_amphorae)
