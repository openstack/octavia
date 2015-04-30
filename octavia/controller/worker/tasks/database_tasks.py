# Copyright 2015 Hewlett-Packard Development Company, L.P.
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
#

import logging

from oslo_utils import uuidutils
from taskflow import task

from octavia.common import constants
from octavia.db import api as db_apis
from octavia.db import repositories as repo
from octavia.i18n import _LW

LOG = logging.getLogger(__name__)


class BaseDatabaseTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        self.amphora_repo = repo.AmphoraRepository()
        self.health_mon_repo = repo.HealthMonitorRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()
        super(BaseDatabaseTask, self).__init__(**kwargs)


class CreateAmphoraInDB(BaseDatabaseTask):
    """Task to create an initial amphora in the Database."""

    default_provides = constants.AMPHORA

    def execute(self, *args, **kwargs):
        """Creates an pending create amphora record in the database.

        :returns: The amphora object created
        """

        amphora = self.amphora_repo.create(db_apis.get_session(),
                                           id=uuidutils.generate_uuid(),
                                           status=constants.PENDING_CREATE)

        LOG.debug("Created Amphora in DB with id %s" % amphora.id)
        return amphora

    def revert(self, *args, **kwargs):
        """Revert by storing the amphora in error state in the DB

        In a future version we might change the status to DELETED
        if deleting the amphora was successful
        """

        if 'result' not in kwargs:
            return None  # nothing to do

#        amphora = kwargs['result']
# TODO(johnsom) fix
#        LOG.warn(_LW("Reverting create amphora in DB for amp id %s "),
#                 amphora.id)

#        _amphora_repo.update(db_apis.get_session(), amphora.id,
#                                 status=constants.ERROR,
#                                 compute_id=amphora.compute_id)


class DeleteHealthMonitorInDB(BaseDatabaseTask):
    """Delete the health monitor in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, health_mon_id):
        """Delete the health monitor in DB

        :param health_mon_id: The health monitor id to delete
        :returns: None
        """

        LOG.debug("DB delete health monitor for id: %s " %
                  health_mon_id)
        self.health_mon_repo.delete(db_apis.get_session(), health_mon_id)

    def revert(self, health_mon_id, *args, **kwargs):
        """Mark the health monitor ERROR since the mark active couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting mark health monitor delete in DB "
                     "for health monitor id %s"), health_mon_id)
# TODO(johnsom) fix this
#        self.health_mon_repo.update(db_apis.get_session(), health_mon.id,
#                                    provisioning_status=constants.ERROR)


class DeleteMemberInDB(BaseDatabaseTask):
    """Delete the member in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, member_id):
        """Delete the member in the DB

        :param member_id: The member ID to be deleted
        :returns: None
        """

        LOG.debug("DB delete member for id: %s " %
                  member_id)
        self.member_repo.delete(db_apis.get_session(), member_id)

    def revert(self, member_id, *args, **kwargs):
        """Mark the member ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting delete in DB "
                     "for member id %s"), member_id)
# TODO(johnsom) fix this
#        self.member_repo.update(db_apis.get_session(), member.id,
#                                operating_status=constants.ERROR)


class DeletePoolInDB(BaseDatabaseTask):
    """Delete the pool in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, pool_id):
        """Delete the pool in DB

        :param pool_id: The pool ID to be deleted
        :returns: None
        """

        LOG.debug("Delete in DB for pool id: %s " %
                  pool_id)
        self.pool_repo.delete(db_apis.get_session(), pool_id)

    def revert(self, pool_id, *args, **kwargs):
        """Mark the pool ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting delete in DB "
                     "for pool id %s"), pool_id)
# TODO(johnsom) Fix this
#        self.pool_repo.update(db_apis.get_session(), pool.id,
#                              operating_status=constants.ERROR)


class GetAmphoraByID(BaseDatabaseTask):
    """Get an amphora object from the database."""

    def execute(self, amphora):
        """Get an amphora object from the database.

        :param amphora_id: The amphora ID to lookup
        :returns: The amphora object
        """

        LOG.debug("Get amphora from DB for amphora id: %s " %
                  amphora.id)
        return self.amphora_repo.get(db_apis.get_session(), id=amphora.id)


class GetLoadbalancerByID(BaseDatabaseTask):
    """Get an load balancer object from the database."""

    def execute(self, loadbalancer):
        """Get an load balancer object from the database.

        :param loadbalancer_id: The load balancer ID to lookup
        :returns: The load balancer object
        """

        LOG.debug("Get load balancer from DB for load balancer id: %s " %
                  loadbalancer.id)
        return self.loadbalancer_repo.get(db_apis.get_session(),
                                          id=loadbalancer.id)


class MapLoadbalancerToAmphora(BaseDatabaseTask):
    """Maps and assigns a load balancer to an amphora in the database."""

    def execute(self, loadbalancer):
        """Allocates an Amphora for the load balancer in the database.

        :param lb_id: The load balancer id to map to an amphora
        :returns: Amphora ID if one was allocated, None if it was
                  unable to allocate an Amphora
        """

        LOG.debug("Allocating an Amphora for load balancer with id %s" %
                  loadbalancer.id)

        amp = self.amphora_repo.allocate_and_associate(
            db_apis.get_session(),
            loadbalancer.id)
        if amp is None:
            LOG.debug("No Amphora available for load balancer with id %s" %
                      loadbalancer.id)
        else:
            LOG.debug("Allocated Amphora with id %s for load balancer "
                      "with id %s" % (amp.id, loadbalancer.id))
        return amp


class MarkAmphoraAllocatedInDB(BaseDatabaseTask):
    """Will mark an amphora as allocated to a load balancer in the database.

    Assume sqlalchemy made sure the DB got
    retried sufficiently - so just abort
    """

    def execute(self, amphora, loadbalancer):
        """Mark amphora as allocated to a load balancer in DB."""

        LOG.debug("Mark ALLOCATED in DB for amphora: %s with compute id %s "
                  "for load balancer: %s" %
                  (amphora.id, amphora.compute_id, loadbalancer.id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.AMPHORA_ALLOCATED,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip,
                                 load_balancer_id=loadbalancer.id)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora ready in DB for amp "
                     "id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR)


class MarkAmphoraBootingInDB(BaseDatabaseTask):
    """Mark the amphora as booting in the database."""

    def execute(self, amphora):
        """Mark amphora booting in DB."""

        LOG.debug("Mark BOOTING in DB for amphora: %s with compute id %s" %
                  (amphora.id, amphora.compute_id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.AMPHORA_BOOTING,
                                 compute_id=amphora.compute_id)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora booting in DB for amp "
                     "id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR,
                                 compute_id=amphora.compute_id)


class MarkAmphoraDeletedInDB(BaseDatabaseTask):
    """Mark the amphora deleted in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, amphora):
        """Mark the amphora as pending delete in DB."""

        LOG.debug("Mark DELETED in DB for amphora: %s "
                  "with compute id %s" %
                  (amphora.id, amphora.compute_id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.DELETED)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora deleted in DB "
                     "for amp id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR)


class MarkAmphoraPendingDeleteInDB(BaseDatabaseTask):
    """Mark the amphora pending delete in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, amphora):
        """Mark the amphora as pending delete in DB."""

        LOG.debug("Mark PENDING DELETE in DB for amphora: %s "
                  "with compute id %s" %
                  (amphora.id, amphora.compute_id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.PENDING_DELETE)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora pending delete in DB "
                     "for amp id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR)


class MarkAmphoraPendingUpdateInDB(BaseDatabaseTask):
    """Mark the amphora pending update in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, amphora):
        """Mark the amphora as pending upate in DB."""

        LOG.debug("Mark PENDING UPDATE in DB for amphora: %s "
                  "with compute id %s" %
                  (amphora.id, amphora.compute_id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.PENDING_UPDATE)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora pending update in DB "
                     "for amp id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR)


class MarkAmphoraReadyInDB(BaseDatabaseTask):
    """This task will mark an amphora as ready in the database.

    Assume sqlalchemy made sure the DB got
    retried sufficiently - so just abort
    """

    def execute(self, amphora):
        """Mark amphora as ready in DB."""

        LOG.debug("Mark BOOTING in DB for amphora: %s with compute id %s" %
                  (amphora.id, amphora.compute_id))
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.AMPHORA_READY,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark amphora ready in DB for amp "
                     "id %(amp)s and compute id %(comp)s"),
                 {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip)


class MarkLBActiveInDB(BaseDatabaseTask):
    """Mark the load balancer active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer):
        """Mark the load balancer as active in DB."""

        LOG.debug("Mark ACTIVE in DB for load balancer id: %s" %
                  loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ACTIVE)

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark load balancer deleted in DB "
                     "for load balancer id %s"), loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)


class MarkLBDeletedInDB(BaseDatabaseTask):
    """Mark the load balancer deleted in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer):
        """Mark the load balancer as deleted in DB."""

        LOG.debug("Mark DELETED in DB for load balancer id: %s" %
                  loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.DELETED)

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark load balancer deleted in DB "
                     "for load balancer id %s"), loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)


class MarkLBPendingDeleteInDB(BaseDatabaseTask):
    """Mark the load balancer pending delete in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer):
        """Mark the load balancer as pending delete in DB."""

        LOG.debug("Mark PENDING DELETE in DB for load balancer id: %s" %
                  loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=(constants.
                                                           PENDING_DELETE))

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark load balancer pending delete in DB "
                     "for load balancer id %s"), loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)


class MarkLBAndListenerActiveInDB(BaseDatabaseTask):
    """Mark the load balancer and listener active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer, listener):
        """Mark the load balancer and listener as active in DB."""

        LOG.debug("Mark ACTIVE in DB for load balancer id: %s "
                  "and listener id: %s" % (loadbalancer.id, listener.id))
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ACTIVE)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ACTIVE)

    def revert(self, loadbalancer, listener, *args, **kwargs):
        """Mark the load balancer and listener as broken."""

        LOG.warn(_LW("Reverting mark load balancer "
                     "and listener active in DB "
                     "for load balancer id %(LB)s and "
                     "listener id: %(list)s"),
                 {'LB': loadbalancer.id, 'list': listener.id})
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class MarkListenerActiveInDB(BaseDatabaseTask):
    """Mark the listener active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener):
        """Mark the listener as active in DB

        :param listener: The listener to be marked deleted
        :returns: None
        """

        LOG.debug("Mark ACTIVE in DB for listener id: %s " %
                  listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ACTIVE)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting mark listener deleted in DB "
                     "for listener id %s"), listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class MarkListenerDeletedInDB(BaseDatabaseTask):
    """Mark the listener deleted in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener):
        """Mark the listener as deleted in DB

        :param listener: The listener to be marked deleted
        :returns: None
        """

        LOG.debug("Mark DELETED in DB for listener id: %s " %
                  listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.DELETED)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting mark listener deleted in DB "
                     "for listener id %s"), listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class MarkListenerPendingDeleteInDB(BaseDatabaseTask):
    """Mark the listener pending delete in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener):
        """Mark the listener as pending delete in DB."""

        LOG.debug("Mark PENDING DELETE in DB for listener id: %s" %
                  listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.PENDING_DELETE)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener as broken and ready to be cleaned up."""

        LOG.warn(_LW("Reverting mark listener pending delete in DB "
                     "for listener id %s"), listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class UpdateHealthMonInDB(BaseDatabaseTask):
    """Update the health monitor in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, health_mon, update_dict):
        """Update the health monitor in the DB

        :param health_mon: The health monitor to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for health monitor id: %s " %
                  health_mon.pool_id)
        self.health_mon_repo.update(db_apis.get_session(), health_mon.pool_id,
                                    **update_dict)

    def revert(self, health_mon, *args, **kwargs):
        """Mark the health monitor ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting update health monitor in DB "
                     "for health monitor id %s"), health_mon.pool_id)
# TODO(johnsom) fix this to set the upper ojects to ERROR
        self.health_mon_repo.update(db_apis.get_session(), health_mon.pool_id,
                                    enabled=0)


class UpdateListenerInDB(BaseDatabaseTask):
    """Update the listener in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener, update_dict):
        """Update the listener in the DB

        :param listener: The listener to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for listener id: %s " %
                  listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  **update_dict)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting update listener in DB "
                     "for listener id %s"), listener.id)
# TODO(johnsom) fix this to set the upper ojects to ERROR
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  enabled=0)


class UpdateMemberInDB(BaseDatabaseTask):
    """Update the member in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, member, update_dict):
        """Update the member in the DB

        :param member: The member to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for member id: %s " %
                  member.id)
        self.member_repo.update(db_apis.get_session(), member.id,
                                **update_dict)

    def revert(self, member, *args, **kwargs):
        """Mark the member ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting update member in DB "
                     "for member id %s"), member.id)
# TODO(johnsom) fix this to set the upper ojects to ERROR
        self.member_repo.update(db_apis.get_session(), member.id,
                                enabled=0)


class UpdatePoolInDB(BaseDatabaseTask):
    """Update the pool in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, pool, update_dict):
        """Update the pool in the DB

        :param pool: The pool to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for pool id: %s " %
                  pool.id)
        self.pool_repo.update(db_apis.get_session(), pool.id,
                              **update_dict)

    def revert(self, pool, *args, **kwargs):
        """Mark the pool ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warn(_LW("Reverting update pool in DB "
                     "for pool id %s"), pool.id)
# TODO(johnsom) fix this to set the upper ojects to ERROR
        self.pool_repo.update(db_apis.get_session(), pool.id,
                              enabled=0)
