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

from oslo_config import cfg
from oslo_db import exception as odb_exceptions
from oslo_utils import uuidutils
import sqlalchemy
from sqlalchemy.orm import exc
from taskflow import task
from taskflow.types import failure

from octavia.common import constants
from octavia.common import data_models
import octavia.common.tls_utils.cert_parser as cert_parser
from octavia.db import api as db_apis
from octavia.db import repositories as repo
from octavia.i18n import _LI, _LW

CONF = cfg.CONF
LOG = logging.getLogger(__name__)
CONF.import_group('keepalived_vrrp', 'octavia.common.config')


class BaseDatabaseTask(task.Task):
    """Base task to load drivers common to the tasks."""

    def __init__(self, **kwargs):
        self.repos = repo.Repositories()
        self.amphora_repo = repo.AmphoraRepository()
        self.health_mon_repo = repo.HealthMonitorRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()
        self.amp_health_repo = repo.AmphoraHealthRepository()
        self.l7policy_repo = repo.L7PolicyRepository()
        self.l7rule_repo = repo.L7RuleRepository()
        super(BaseDatabaseTask, self).__init__(**kwargs)

    def _delete_from_amp_health(self, amphora_id):
        """Delete the amphora_health record for an amphora.

        :param amphora_id: The amphora id to delete
        """
        LOG.debug('Disabling health monitoring on amphora: %s', amphora_id)
        try:
            self.amp_health_repo.delete(db_apis.get_session(),
                                        amphora_id=amphora_id)
        except (sqlalchemy.orm.exc.NoResultFound,
                sqlalchemy.orm.exc.UnmappedInstanceError):
            LOG.debug('No existing amphora health record to delete '
                      'for amphora: %s, skipping.', amphora_id)

    def _mark_amp_health_busy(self, amphora_id):
        """Mark the amphora_health record busy for an amphora.

        :param amphora_id: The amphora id to mark busy
        """
        LOG.debug('Marking health monitoring busy on amphora: %s', amphora_id)
        try:
            self.amp_health_repo.update(db_apis.get_session(),
                                        amphora_id=amphora_id,
                                        busy=True)
        except (sqlalchemy.orm.exc.NoResultFound,
                sqlalchemy.orm.exc.UnmappedInstanceError):
            LOG.debug('No existing amphora health record to mark busy '
                      'for amphora: %s, skipping.', amphora_id)


class CreateAmphoraInDB(BaseDatabaseTask):
    """Task to create an initial amphora in the Database."""

    def execute(self, *args, **kwargs):
        """Creates an pending create amphora record in the database.

        :returns: The amphora object created
        """

        amphora = self.amphora_repo.create(db_apis.get_session(),
                                           id=uuidutils.generate_uuid(),
                                           status=constants.PENDING_CREATE,
                                           cert_busy=False)

        LOG.info(_LI("Created Amphora in DB with id %s"), amphora.id)
        return amphora.id

    def revert(self, result, *args, **kwargs):
        """Revert by storing the amphora in error state in the DB

        In a future version we might change the status to DELETED
        if deleting the amphora was successful
        """

        if isinstance(result, failure.Failure):
            # This task's execute failed, so nothing needed to be done to
            # revert
            return

        # At this point the revert is being called because another task
        # executed after this failed so we will need to do something and
        # result is the amphora's id

        LOG.warning(_LW("Reverting create amphora in DB for amp id %s "),
                    result)

        # Delete the amphora for now. May want to just update status later
        self.amphora_repo.delete(db_apis.get_session(), id=result)


class MarkLBAmphoraeDeletedInDB(BaseDatabaseTask):
    """Task to mark a list of amphora deleted in the Database."""

    def execute(self, loadbalancer):
        """Update amphorae statuses to DELETED in the database.

        """
        for amp in loadbalancer.amphorae:
            LOG.debug("Marking amphora %s DELETED ", amp.id)
            self.amphora_repo.update(db_apis.get_session(),
                                     id=amp.id, status=constants.DELETED)


class DeleteHealthMonitorInDB(BaseDatabaseTask):
    """Delete the health monitor in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, pool_id):
        """Delete the health monitor in DB

        :param health_mon_id: The health monitor id to delete
        :returns: None
        """

        LOG.debug("DB delete health monitor for id: %s ", pool_id)
        try:
            self.health_mon_repo.delete(db_apis.get_session(), pool_id=pool_id)
        except exc.NoResultFound:
            # ignore if the HelathMonitor was not found
            pass

    def revert(self, pool_id, *args, **kwargs):
        """Mark the health monitor ERROR since the mark active couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting mark health monitor delete in DB "
                        "for health monitor on pool with id %s"), pool_id)
# TODO(johnsom) fix this
#        self.health_mon_repo.update(db_apis.get_session(), health_mon.id,
#                                    provisioning_status=constants.ERROR)


class DeleteHealthMonitorInDBByPool(DeleteHealthMonitorInDB):
    """Delete the health monitor in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, pool):
        super(DeleteHealthMonitorInDBByPool, self).execute(pool.id)

    def revert(self, pool, *args, **kwargs):
        super(DeleteHealthMonitorInDBByPool, self).revert(
            pool.id, *args, **kwargs)


class DeleteMemberInDB(BaseDatabaseTask):
    """Delete the member in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, member):
        """Delete the member in the DB

        :param member: The member to be deleted
        :returns: None
        """

        LOG.debug("DB delete member for id: %s ", member.id)
        self.member_repo.delete(db_apis.get_session(), id=member.id)

    def revert(self, member, *args, **kwargs):
        """Mark the member ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting delete in DB "
                        "for member id %s"), member.id)
# TODO(johnsom) fix this
#        self.member_repo.update(db_apis.get_session(), member.id,
#                                operating_status=constants.ERROR)


class DeleteListenerInDB(BaseDatabaseTask):
    """Delete the listener in the DB."""

    def execute(self, listener):
        """Delete the listener in DB

        :param listener: The listener to delete
        :returns: None
        """
        LOG.debug("Delete in DB for listener id: %s", listener.id)
        self.listener_repo.delete(db_apis.get_session(), id=listener.id)

    def revert(self, listener_id, *args, **kwargs):
        """Mark the listener ERROR since the listener didn't delete

        :returns: None
        """

        LOG.warning(_LW("Reverting mark listener delete in DB "
                        "for listener id %s"), listener_id)


class DeletePoolInDB(BaseDatabaseTask):
    """Delete the pool in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, pool):
        """Delete the pool in DB

        :param pool: The pool to be deleted
        :returns: None
        """

        LOG.debug("Delete in DB for pool id: %s ", pool.id)
        self.pool_repo.delete(db_apis.get_session(), id=pool.id)

    def revert(self, pool_id, *args, **kwargs):
        """Mark the pool ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting delete in DB "
                        "for pool id %s"), pool_id)
# TODO(johnsom) Fix this
#        self.pool_repo.update(db_apis.get_session(), pool.id,
#                              operating_status=constants.ERROR)


class DeleteL7PolicyInDB(BaseDatabaseTask):
    """Delete the L7 policy in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, l7policy):
        """Delete the l7policy in DB

        :param l7policy: The l7policy to be deleted
        :returns: None
        """

        LOG.debug("Delete in DB for l7policy id: %s ", l7policy.id)
        self.l7policy_repo.delete(db_apis.get_session(), id=l7policy.id)

    def revert(self, l7policy_id, *args, **kwargs):
        """Mark the l7policy ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting delete in DB "
                        "for l7policy id %s"), l7policy_id)
# TODO(sbalukoff) Fix this
#        self.listener_repo.update(db_apis.get_session(), l7policy.listener.id,
#                                  operating_status=constants.ERROR)


class DeleteL7RuleInDB(BaseDatabaseTask):
    """Delete the L7 rule in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, l7rule):
        """Delete the l7rule in DB

        :param l7rule: The l7rule to be deleted
        :returns: None
        """

        LOG.debug("Delete in DB for l7rule id: %s ", l7rule.id)
        self.l7rule_repo.delete(db_apis.get_session(), id=l7rule.id)

    def revert(self, l7rule_id, *args, **kwargs):
        """Mark the l7rule ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting delete in DB "
                        "for l7rule id %s"), l7rule_id)
# TODO(sbalukoff) Fix this
#        self.listener_repo.update(db_apis.get_session(),
#                                  l7rule.l7policy.listener.id,
#                                  operating_status=constants.ERROR)


class ReloadAmphora(BaseDatabaseTask):
    """Get an amphora object from the database."""

    def execute(self, amphora_id):
        """Get an amphora object from the database.

        :param amphora_id: The amphora ID to lookup
        :returns: The amphora object
        """

        LOG.debug("Get amphora from DB for amphora id: %s ", amphora_id)
        return self.amphora_repo.get(db_apis.get_session(), id=amphora_id)


class ReloadLoadBalancer(BaseDatabaseTask):
    """Get an load balancer object from the database."""

    def execute(self, loadbalancer_id, *args, **kwargs):
        """Get an load balancer object from the database.

        :param loadbalancer_id: The load balancer ID to lookup
        :returns: The load balancer object
        """

        LOG.debug("Get load balancer from DB for load balancer id: %s ",
                  loadbalancer_id)
        return self.loadbalancer_repo.get(db_apis.get_session(),
                                          id=loadbalancer_id)


class UpdateVIPAfterAllocation(BaseDatabaseTask):

    def execute(self, loadbalancer_id, vip):
        self.repos.vip.update(db_apis.get_session(), loadbalancer_id,
                              port_id=vip.port_id, subnet_id=vip.subnet_id,
                              ip_address=vip.ip_address)
        return self.repos.load_balancer.get(db_apis.get_session(),
                                            id=loadbalancer_id)


class UpdateAmphoraVIPData(BaseDatabaseTask):

    def execute(self, amps_data):
        for amp_data in amps_data:
            self.repos.amphora.update(db_apis.get_session(), amp_data.id,
                                      vrrp_ip=amp_data.vrrp_ip,
                                      ha_ip=amp_data.ha_ip,
                                      vrrp_port_id=amp_data.vrrp_port_id,
                                      ha_port_id=amp_data.ha_port_id,
                                      vrrp_id=1)


class UpdateAmpFailoverDetails(BaseDatabaseTask):
    """Update amphora failover details in the database."""

    def execute(self, amphora, amp_data):
        """Update amphora failover details in the database.

        :param loadbalancer_id: The load balancer ID to lookup
        :param mps_data: The load balancer ID to lookup
        """
        self.repos.amphora.update(db_apis.get_session(), amphora.id,
                                  vrrp_ip=amp_data.vrrp_ip,
                                  ha_ip=amp_data.ha_ip,
                                  vrrp_port_id=amp_data.vrrp_port_id,
                                  ha_port_id=amp_data.ha_port_id,
                                  role=amp_data.role,
                                  vrrp_id=amp_data.vrrp_id,
                                  vrrp_priority=amp_data.vrrp_priority)


class AssociateFailoverAmphoraWithLBID(BaseDatabaseTask):

    def execute(self, amphora_id, loadbalancer_id):
        self.repos.amphora.associate(db_apis.get_session(),
                                     load_balancer_id=loadbalancer_id,
                                     amphora_id=amphora_id)

    def revert(self, amphora_id, *args, **kwargs):
        self.repos.amphora.update(db_apis.get_session(), amphora_id,
                                  loadbalancer_id=None)


class MapLoadbalancerToAmphora(BaseDatabaseTask):
    """Maps and assigns a load balancer to an amphora in the database."""

    def execute(self, loadbalancer_id):
        """Allocates an Amphora for the load balancer in the database.

        :param lb_id: The load balancer id to map to an amphora
        :returns: Amphora ID if one was allocated, None if it was
                  unable to allocate an Amphora
        """

        LOG.debug("Allocating an Amphora for load balancer with id %s",
                  loadbalancer_id)

        amp = self.amphora_repo.allocate_and_associate(
            db_apis.get_session(),
            loadbalancer_id)
        if amp is None:
            LOG.debug("No Amphora available for load balancer with id %s",
                      loadbalancer_id)
            return None

        LOG.debug("Allocated Amphora with id %(amp)s for load balancer "
                  "with id %(lb)s", {'amp': amp.id, 'lb': loadbalancer_id})

        return amp.id

    def revert(self, result, loadbalancer_id, *args, **kwargs):
        LOG.warning(_LW("Reverting Amphora allocation for the load "
                        "balancer %s in the database."), loadbalancer_id)

        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer_id,
                                      provisioning_status=constants.ERROR)


class _MarkAmphoraRoleAndPriorityInDB(BaseDatabaseTask):
    """Alter the amphora role in DB."""

    def _execute(self, amphora, amp_role, vrrp_priority):
        LOG.debug("Mark %(role)s in DB for amphora: %(amp)s",
                  {'role': amp_role, 'amp': amphora.id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 role=amp_role,
                                 vrrp_priority=vrrp_priority)

    def _revert(self, result, amphora, *args, **kwargs):
        """Assigns None role and vrrp_priority."""

        if isinstance(result, failure.Failure):
            return

        LOG.warning(_LW("Reverting amphora role in DB for amp "
                        "id %(amp)s"),
                    {'amp': amphora.id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 role=None,
                                 vrrp_priority=None)


class MarkAmphoraMasterInDB(_MarkAmphoraRoleAndPriorityInDB):
    """Alter the amphora role to: MASTER."""

    def execute(self, amphora):
        """Mark amphora as allocated to a load balancer in DB."""
        amp_role = constants.ROLE_MASTER
        self._execute(amphora, amp_role, constants.ROLE_MASTER_PRIORITY)

    def revert(self, result, amphora, *args, **kwargs):
        self._revert(result, amphora, *args, **kwargs)


class MarkAmphoraBackupInDB(_MarkAmphoraRoleAndPriorityInDB):
    """Alter the amphora role to: Backup."""

    def execute(self, amphora):
        amp_role = constants.ROLE_BACKUP
        self._execute(amphora, amp_role, constants.ROLE_BACKUP_PRIORITY)

    def revert(self, result, amphora, *args, **kwargs):
        self._revert(result, amphora, *args, **kwargs)


class MarkAmphoraStandAloneInDB(_MarkAmphoraRoleAndPriorityInDB):
    """Alter the amphora role to: Standalone."""

    def execute(self, amphora):
        amp_role = constants.ROLE_STANDALONE
        self._execute(amphora, amp_role, None)

    def revert(self, result, amphora, *args, **kwargs):
        self._revert(result, amphora, *args, **kwargs)


class MarkAmphoraAllocatedInDB(BaseDatabaseTask):
    """Will mark an amphora as allocated to a load balancer in the database.

    Assume sqlalchemy made sure the DB got
    retried sufficiently - so just abort
    """

    def execute(self, amphora, loadbalancer_id):
        """Mark amphora as allocated to a load balancer in DB."""

        LOG.info(_LI("Mark ALLOCATED in DB for amphora: %(amp)s with "
                     "compute id %(comp)s for load balancer: %(lb)s"),
                 {"amp": amphora.id, "comp": amphora.compute_id,
                  "lb": loadbalancer_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.AMPHORA_ALLOCATED,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip,
                                 load_balancer_id=loadbalancer_id)

    def revert(self, result, amphora, loadbalancer_id, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        if isinstance(result, failure.Failure):
            return

        LOG.warning(_LW("Reverting mark amphora ready in DB for amp "
                        "id %(amp)s and compute id %(comp)s"),
                    {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR)


class MarkAmphoraBootingInDB(BaseDatabaseTask):
    """Mark the amphora as booting in the database."""

    def execute(self, amphora_id, compute_id):
        """Mark amphora booting in DB."""

        LOG.debug("Mark BOOTING in DB for amphora: %(amp)s with "
                  "compute id %(id)s", {'amp': amphora_id, 'id': compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora_id,
                                 status=constants.AMPHORA_BOOTING,
                                 compute_id=compute_id)

    def revert(self, result, amphora_id, compute_id, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        if isinstance(result, failure.Failure):
            return

        LOG.warning(_LW("Reverting mark amphora booting in DB for amp "
                        "id %(amp)s and compute id %(comp)s"),
                    {'amp': amphora_id, 'comp': compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora_id,
                                 status=constants.ERROR,
                                 compute_id=compute_id)


class MarkAmphoraDeletedInDB(BaseDatabaseTask):
    """Mark the amphora deleted in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, amphora):
        """Mark the amphora as pending delete in DB."""

        LOG.debug("Mark DELETED in DB for amphora: %(amp)s with "
                  "compute id %(comp)s",
                  {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.DELETED)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark amphora deleted in DB "
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

        LOG.debug("Mark PENDING DELETE in DB for amphora: %(amp)s "
                  "with compute id %(id)s",
                  {'amp': amphora.id, 'id': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.PENDING_DELETE)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark amphora pending delete in DB "
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

        LOG.debug("Mark PENDING UPDATE in DB for amphora: %(amp)s "
                  "with compute id %(id)s",
                  {'amp': amphora.id, 'id': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.PENDING_UPDATE)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark amphora pending update in DB "
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

        LOG.info(_LI("Mark READY in DB for amphora: %(amp)s with compute "
                     "id %(comp)s"),
                 {"amp": amphora.id, "comp": amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.AMPHORA_READY,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip)

    def revert(self, amphora, *args, **kwargs):
        """Mark the amphora as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark amphora ready in DB for amp "
                        "id %(amp)s and compute id %(comp)s"),
                    {'amp': amphora.id, 'comp': amphora.compute_id})
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 status=constants.ERROR,
                                 compute_id=amphora.compute_id,
                                 lb_network_ip=amphora.lb_network_ip)


class UpdateAmphoraComputeId(BaseDatabaseTask):

    def execute(self, amphora_id, compute_id):
        self.amphora_repo.update(db_apis.get_session(), amphora_id,
                                 compute_id=compute_id)


class UpdateAmphoraInfo(BaseDatabaseTask):

    def execute(self, amphora_id, compute_obj):
        self.amphora_repo.update(db_apis.get_session(), amphora_id,
                                 lb_network_ip=compute_obj.lb_network_ip)
        return self.amphora_repo.get(db_apis.get_session(), id=amphora_id)


class UpdateAmphoraDBCertExpiration(BaseDatabaseTask):
    """Update the amphora expiration date with new cert file date."""

    def execute(self, amphora_id, server_pem):
        LOG.debug("Update DB cert expiry date of amphora id: %s", amphora_id)
        cert_expiration = cert_parser.get_cert_expiration(server_pem)
        LOG.debug("Certificate expiration date is %s ", cert_expiration)
        self.amphora_repo.update(db_apis.get_session(), amphora_id,
                                 cert_expiration=cert_expiration)


class UpdateAmphoraCertBusyToFalse(BaseDatabaseTask):
    """Update the amphora cert_busy flag to be false."""
    def execute(self, amphora):
        self.amphora_repo.update(db_apis.get_session(), amphora.id,
                                 cert_busy=False)


class MarkLBActiveInDB(BaseDatabaseTask):
    """Mark the load balancer active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def __init__(self, mark_listeners=False, **kwargs):
        super(MarkLBActiveInDB, self).__init__(**kwargs)
        self.mark_listeners = mark_listeners

    def execute(self, loadbalancer):
        """Mark the load balancer as active in DB."""

        if self.mark_listeners:
            LOG.debug("Marking all listeners of loadbalancer %s ACTIVE",
                      loadbalancer.id)
            for listener in loadbalancer.listeners:
                self.listener_repo.update(db_apis.get_session(),
                                          listener.id,
                                          provisioning_status=constants.ACTIVE)

        LOG.info(_LI("Mark ACTIVE in DB for load balancer id: %s"),
                 loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ACTIVE)

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        if self.mark_listeners:
            LOG.debug("Marking all listeners of loadbalancer %s ERROR",
                      loadbalancer.id)
            for listener in loadbalancer.listeners:
                try:
                    self.listener_repo.update(
                        db_apis.get_session(), listener.id,
                        provisioning_status=constants.ERROR)
                except Exception:
                    LOG.warning(_LW("Error updating listener %s provisioning "
                                    "status"), listener.id)

        LOG.warning(_LW("Reverting mark load balancer deleted in DB "
                        "for load balancer id %s"), loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)


class UpdateLBServerGroupInDB(BaseDatabaseTask):
    """Update the server group id info for load balancer in DB."""

    def execute(self, loadbalancer_id, server_group_id):
        LOG.debug("Server Group updated with id: %s for load balancer id: %s:",
                  server_group_id, loadbalancer_id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      id=loadbalancer_id,
                                      server_group_id=server_group_id)

    def revert(self, loadbalancer_id, server_group_id, *args, **kwargs):
        LOG.warning(_LW('Reverting Server Group updated with id: %(s1)s for '
                        'load balancer id: %(s2)s '),
                    {'s1': server_group_id, 's2': loadbalancer_id})
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      id=loadbalancer_id,
                                      server_group_id=None)


class MarkLBDeletedInDB(BaseDatabaseTask):
    """Mark the load balancer deleted in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer):
        """Mark the load balancer as deleted in DB."""

        LOG.debug("Mark DELETED in DB for load balancer id: %s",
                  loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.DELETED)

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark load balancer deleted in DB "
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

        LOG.debug("Mark PENDING DELETE in DB for load balancer id: %s",
                  loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=(constants.
                                                           PENDING_DELETE))

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the load balancer as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark load balancer pending delete in DB "
                        "for load balancer id %s"), loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)


class MarkLBAndListenersActiveInDB(BaseDatabaseTask):
    """Mark the load balancer and specified listeners active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer, listeners):
        """Mark the load balancer and listeners as active in DB."""

        LOG.debug("Mark ACTIVE in DB for load balancer id: %s "
                  "and listener ids: %s", loadbalancer.id,
                  ', '.join([l.id for l in listeners]))
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ACTIVE)
        for listener in listeners:
            self.listener_repo.update(db_apis.get_session(), listener.id,
                                      provisioning_status=constants.ACTIVE)

    def revert(self, loadbalancer, listeners, *args, **kwargs):
        """Mark the load balancer and listeners as broken."""

        LOG.warning(_LW("Reverting mark load balancer "
                        "and listeners active in DB "
                        "for load balancer id %(LB)s and "
                        "listener ids: %(list)s"),
                    {'LB': loadbalancer.id,
                     'list': ', '.join([l.id for l in listeners])})
        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
                                      provisioning_status=constants.ERROR)
        for listener in listeners:
            try:
                self.listener_repo.update(db_apis.get_session(), listener.id,
                                          provisioning_status=constants.ERROR)
            except Exception:
                LOG.warning(_LW("Failed to update listener %s provisioning "
                                "status..."), listener.id)


class MarkListenerActiveInDB(BaseDatabaseTask):
    """Mark the listener active in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener):
        """Mark the listener as active in DB

        :param listener: The listener to be marked deleted
        :returns: None
        """

        LOG.debug("Mark ACTIVE in DB for listener id: %s ", listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ACTIVE)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting mark listener deleted in DB "
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

        LOG.debug("Mark DELETED in DB for listener id: %s ", listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.DELETED)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the delete couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting mark listener deleted in DB "
                        "for listener id %s"), listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class MarkListenerPendingDeleteInDB(BaseDatabaseTask):
    """Mark the listener pending delete in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, listener):
        """Mark the listener as pending delete in DB."""

        LOG.debug("Mark PENDING DELETE in DB for listener id: %s",
                  listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.PENDING_DELETE)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener as broken and ready to be cleaned up."""

        LOG.warning(_LW("Reverting mark listener pending delete in DB "
                        "for listener id %s"), listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  provisioning_status=constants.ERROR)


class UpdateLoadbalancerInDB(BaseDatabaseTask):
    """Update the loadbalancer in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, loadbalancer, update_dict):
        """Update the loadbalancer in the DB

        :param loadbalancer: The listener to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for loadbalancer id: %s ", loadbalancer.id)
        self.loadbalancer_repo.update(db_apis.get_session(), loadbalancer.id,
                                      **update_dict)

    def revert(self, loadbalancer, *args, **kwargs):
        """Mark the loadbalancer ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update loadbalancer in DB "
                        "for loadbalancer id %s"), loadbalancer.id)

        self.loadbalancer_repo.update(db_apis.get_session(),
                                      loadbalancer.id,
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

        LOG.debug("Update DB for health monitor id: %s ", health_mon.pool_id)
        self.health_mon_repo.update(db_apis.get_session(), health_mon.pool_id,
                                    **update_dict)

    def revert(self, health_mon, *args, **kwargs):
        """Mark the health monitor ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update health monitor in DB "
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

        LOG.debug("Update DB for listener id: %s ", listener.id)
        self.listener_repo.update(db_apis.get_session(), listener.id,
                                  **update_dict)

    def revert(self, listener, *args, **kwargs):
        """Mark the listener ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update listener in DB "
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

        LOG.debug("Update DB for member id: %s ", member.id)
        self.member_repo.update(db_apis.get_session(), member.id,
                                **update_dict)

    def revert(self, member, *args, **kwargs):
        """Mark the member ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update member in DB "
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

        LOG.debug("Update DB for pool id: %s ", pool.id)
        self.repos.update_pool_and_sp(db_apis.get_session(), pool.id,
                                      update_dict)

    def revert(self, pool, *args, **kwargs):
        """Mark the pool ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update pool in DB "
                        "for pool id %s"), pool.id)
# TODO(johnsom) fix this to set the upper ojects to ERROR
        self.repos.update_pool_and_sp(db_apis.get_session(),
                                      pool.id, {'enabled': 0})


class UpdateL7PolicyInDB(BaseDatabaseTask):
    """Update the L7 policy in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, l7policy, update_dict):
        """Update the L7 policy in the DB

        :param l7policy: The L7 policy to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for l7policy id: %s ", l7policy.id)
        self.l7policy_repo.update(db_apis.get_session(), l7policy.id,
                                  **update_dict)

    def revert(self, l7policy, *args, **kwargs):
        """Mark the l7policy ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update l7policy in DB "
                        "for l7policy id %s"), l7policy.id)
# TODO(sbalukoff) fix this to set the upper objects to ERROR
        self.l7policy_repo.update(db_apis.get_session(), l7policy.id,
                                  enabled=0)


class UpdateL7RuleInDB(BaseDatabaseTask):
    """Update the L7 rule in the DB.

    Since sqlalchemy will likely retry by itself always revert if it fails
    """

    def execute(self, l7rule, update_dict):
        """Update the L7 rule in the DB

        :param l7rule: The L7 rule to be updated
        :param update_dict: The dictionary of updates to apply
        :returns: None
        """

        LOG.debug("Update DB for l7rule id: %s ", l7rule.id)
        self.l7rule_repo.update(db_apis.get_session(), l7rule.id,
                                **update_dict)

    def revert(self, l7rule, *args, **kwargs):
        """Mark the L7 rule ERROR since the update couldn't happen

        :returns: None
        """

        LOG.warning(_LW("Reverting update l7rule in DB "
                        "for l7rule id %s"), l7rule.id)
# TODO(sbalukoff) fix this to set appropriate upper objects to ERROR
        self.l7policy_repo.update(db_apis.get_session(), l7rule.l7policy.id,
                                  enabled=0)


class GetAmphoraDetails(BaseDatabaseTask):
    """Task to retrieve amphora network details."""

    def execute(self, amphora):
        return data_models.Amphora(id=amphora.id,
                                   vrrp_ip=amphora.vrrp_ip,
                                   ha_ip=amphora.ha_ip,
                                   vrrp_port_id=amphora.vrrp_port_id,
                                   ha_port_id=amphora.ha_port_id,
                                   role=amphora.role,
                                   vrrp_id=amphora.vrrp_id,
                                   vrrp_priority=amphora.vrrp_priority)


class GetListenersFromLoadbalancer(BaseDatabaseTask):
    """Task to pull the listener from a loadbalancer."""

    def execute(self, loadbalancer):
        listeners = []
        for listener in loadbalancer.listeners:
            l = self.listener_repo.get(db_apis.get_session(), id=listener.id)
            listeners.append(l)
        return listeners


class GetVipFromLoadbalancer(BaseDatabaseTask):
    """Task to pull the vip from a loadbalancer."""

    def execute(self, loadbalancer):
        return loadbalancer.vip


class CreateVRRPGroupForLB(BaseDatabaseTask):

    def execute(self, loadbalancer):
        try:
            loadbalancer.vrrp_group = self.repos.vrrpgroup.create(
                db_apis.get_session(),
                load_balancer_id=loadbalancer.id,
                vrrp_group_name=str(loadbalancer.id).replace('-', ''),
                vrrp_auth_type=constants.VRRP_AUTH_DEFAULT,
                vrrp_auth_pass=uuidutils.generate_uuid().replace('-', '')[0:7],
                advert_int=CONF.keepalived_vrrp.vrrp_advert_int)
        except odb_exceptions.DBDuplicateEntry:
            LOG.debug('VRRP_GROUP entry already exists for load balancer, '
                      'skipping create.')
        return loadbalancer


class DisableAmphoraHealthMonitoring(BaseDatabaseTask):
    """Disable amphora health monitoring.

    This disables amphora health monitoring by removing it from
    the amphora_health table.
    """

    def execute(self, amphora):
        """Disable health monitoring for an amphora

        :param amphora: The amphora to disable health monitoring for
        """
        self._delete_from_amp_health(amphora.id)


class DisableLBAmphoraeHealthMonitoring(BaseDatabaseTask):
    """Disable health monitoring on the LB amphorae.

    This disables amphora health monitoring by removing it from
    the amphora_health table for each amphora on a load balancer.
    """

    def execute(self, loadbalancer):
        """Disable health monitoring for amphora on a load balancer

        :param loadbalancer: The load balancer to disable health monitoring on
        """
        for amphora in loadbalancer.amphorae:
            self._delete_from_amp_health(amphora.id)


class MarkAmphoraHealthBusy(BaseDatabaseTask):
    """Mark amphora health monitoring busy.

    This prevents amphora failover by marking the amphora busy in
    the amphora_health table.
    """

    def execute(self, amphora):
        """Mark amphora health monitoring busy

        :param amphora: The amphora to mark amphora health busy
        """
        self._mark_amp_health_busy(amphora.id)


class MarkLBAmphoraeHealthBusy(BaseDatabaseTask):
    """Mark amphora health monitoring busy for the LB.

    This prevents amphora failover by marking the amphora busy in
    the amphora_health table for each load balancer.
    """

    def execute(self, loadbalancer):
        """Marks amphora health busy for amphora on a load balancer

        :param loadbalancer: The load balancer to mark amphora health busy
        """
        for amphora in loadbalancer.amphorae:
            self._mark_amp_health_busy(amphora.id)
