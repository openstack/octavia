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

import datetime
import time
import timeit

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import sqlalchemy
from stevedore import driver as stevedore_driver

from octavia.common import constants
from octavia.common import stats
from octavia.controller.healthmanager.health_drivers import update_base
from octavia.db import api as db_api
from octavia.db import repositories as repo

CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class UpdateHealthDb(update_base.HealthUpdateBase):
    def __init__(self):
        super(UpdateHealthDb, self).__init__()
        # first setup repo for amphora, listener,member(nodes),pool repo
        self.amphora_repo = repo.AmphoraRepository()
        self.amphora_health_repo = repo.AmphoraHealthRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()

    def _update_status(self, session, repo, entity_type,
                       entity_id, new_op_status, old_op_status):
        message = {}
        if old_op_status.lower() != new_op_status.lower():
            LOG.debug("%s %s status has changed from %s to "
                      "%s, updating db.",
                      entity_type, entity_id, old_op_status,
                      new_op_status)
            repo.update(session, entity_id, operating_status=new_op_status)
            # Map the status for neutron-lbaas compatibility
            if new_op_status == constants.DRAINING:
                new_op_status = constants.ONLINE
            message.update({constants.OPERATING_STATUS: new_op_status})

    def update_health(self, health, srcaddr):
        # The executor will eat any exceptions from the update_health code
        # so we need to wrap it and log the unhandled exception
        start_time = timeit.default_timer()
        try:
            self._update_health(health, srcaddr)
        except Exception as e:
            LOG.exception('Health update for amphora %(amp)s encountered '
                          'error %(err)s. Skipping health update.',
                          {'amp': health['id'], 'err': e})
        # TODO(johnsom) We need to set a warning threshold here
        LOG.debug('Health Update finished in: %s seconds',
                  timeit.default_timer() - start_time)

    # Health heartbeat messsage pre-versioning with UDP listeners
    # need to adjust the expected listener count
    # This is for backward compatibility with Rocky pre-versioning
    # heartbeat amphora.
    def _update_listener_count_for_UDP(self, session, db_lb,
                                       expected_listener_count):
        # For udp listener, the udp health won't send out by amp agent.
        # Once the default_pool of udp listener have the first enabled
        # member, then the health will be sent out. So during this
        # period, need to figure out the udp listener and ignore them
        # by changing expected_listener_count.
        for list_id, list_db in db_lb.get('listeners', {}).items():
            need_remove = False
            if list_db['protocol'] == constants.PROTOCOL_UDP:
                listener = self.listener_repo.get(session, id=list_id)
                enabled_members = ([member
                                    for member in
                                    listener.default_pool.members
                                    if member.enabled]
                                   if listener.default_pool else [])
                if listener.default_pool:
                    if not listener.default_pool.members:
                        need_remove = True
                    elif not enabled_members:
                        need_remove = True
                else:
                    need_remove = True

                if need_remove:
                    expected_listener_count = expected_listener_count - 1
        return expected_listener_count

    def _update_health(self, health, srcaddr):
        """This function is to update db info based on amphora status

        :param health: map object that contains amphora, listener, member info
        :type map: string
        :returns: null

        The input v1 health data structure is shown as below::

            health = {
                "id": self.FAKE_UUID_1,
                "listeners": {
                    "listener-id-1": {"status": constants.OPEN, "pools": {
                        "pool-id-1": {"status": constants.UP,
                                      "members": {
                                          "member-id-1": constants.ONLINE}
                                      }
                    }
                    }
                }
            }

        Example V2 message::

            {"id": "<amphora_id>",
             "seq": 67,
             "listeners": {
               "<listener_id>": {
                 "status": "OPEN",
                 "stats": {
                   "tx": 0,
                   "rx": 0,
                   "conns": 0,
                   "totconns": 0,
                   "ereq": 0
                 }
               }
             },
             "pools": {
                 "<pool_id>:<listener_id>": {
                   "status": "UP",
                   "members": {
                     "<member_id>": "no check"
                   }
                 }
             },
             "ver": 2
            }

        """
        session = db_api.get_session()

        # We need to see if all of the listeners are reporting in
        db_lb = self.amphora_repo.get_lb_for_health_update(session,
                                                           health['id'])
        ignore_listener_count = False

        if db_lb:
            expected_listener_count = 0
            if 'PENDING' in db_lb['provisioning_status']:
                ignore_listener_count = True
            else:
                for key, listener in db_lb.get('listeners', {}).items():
                    # disabled listeners don't report from the amphora
                    if listener['enabled']:
                        expected_listener_count += 1

                # If this is a heartbeat older than versioning, handle
                # UDP special for backward compatibility.
                if 'ver' not in health:
                    udp_listeners = [
                        l for k, l in db_lb.get('listeners', {}).items()
                        if l['protocol'] == constants.PROTOCOL_UDP]
                    if udp_listeners:
                        expected_listener_count = (
                            self._update_listener_count_for_UDP(
                                session, db_lb, expected_listener_count))
        else:
            # If this is not a spare amp, log and skip it.
            amp = self.amphora_repo.get(session, id=health['id'])
            if not amp or amp.load_balancer_id:
                # This is debug and not warning because this can happen under
                # normal deleting operations.
                LOG.debug('Received a health heartbeat from amphora %s with '
                          'IP %s that should not exist. This amphora may be '
                          'in the process of being deleted, in which case you '
                          'will only see this message a few '
                          'times', health['id'], srcaddr)
                if not amp:
                    LOG.warning('The amphora %s with IP %s is missing from '
                                'the DB, so it cannot be automatically '
                                'deleted (the compute_id is unknown). An '
                                'operator must manually delete it from the '
                                'compute service.', health['id'], srcaddr)
                    return
                # delete the amp right there
                try:
                    compute = stevedore_driver.DriverManager(
                        namespace='octavia.compute.drivers',
                        name=CONF.controller_worker.compute_driver,
                        invoke_on_load=True
                    ).driver
                    compute.delete(amp.compute_id)
                    return
                except Exception as e:
                    LOG.info("Error deleting amp %s with IP %s Error: %s",
                             health['id'], srcaddr, e)
            expected_listener_count = 0

        listeners = health['listeners']

        # Do not update amphora health if the reporting listener count
        # does not match the expected listener count
        if len(listeners) == expected_listener_count or ignore_listener_count:

            lock_session = db_api.get_session(autocommit=False)

            # if we're running too far behind, warn and bail
            proc_delay = time.time() - health['recv_time']
            hb_interval = CONF.health_manager.heartbeat_interval
            # TODO(johnsom) We need to set a warning threshold here, and
            #               escalate to critical when it reaches the
            #               heartbeat_interval
            if proc_delay >= hb_interval:
                LOG.warning('Amphora %(id)s health message was processed too '
                            'slowly: %(delay)ss! The system may be overloaded '
                            'or otherwise malfunctioning. This heartbeat has '
                            'been ignored and no update was made to the '
                            'amphora health entry. THIS IS NOT GOOD.',
                            {'id': health['id'], 'delay': proc_delay})
                return

            # if the input amphora is healthy, we update its db info
            try:
                self.amphora_health_repo.replace(
                    lock_session, health['id'],
                    last_update=(datetime.datetime.utcnow()))
                lock_session.commit()
            except Exception:
                with excutils.save_and_reraise_exception():
                    lock_session.rollback()
        else:
            LOG.warning('Amphora %(id)s health message reports %(found)i '
                        'listeners when %(expected)i expected',
                        {'id': health['id'], 'found': len(listeners),
                         'expected': expected_listener_count})

        # Don't try to update status for spares pool amphora
        if not db_lb:
            return

        processed_pools = []
        potential_offline_pools = {}

        # We got a heartbeat so lb is healthy until proven otherwise
        if db_lb['enabled'] is False:
            lb_status = constants.OFFLINE
        else:
            lb_status = constants.ONLINE

        health_msg_version = health.get('ver', 0)

        for listener_id in db_lb.get('listeners', {}):
            db_op_status = db_lb['listeners'][listener_id]['operating_status']
            listener_status = None
            listener = None

            if listener_id not in listeners:
                listener_status = constants.OFFLINE
            else:
                listener = listeners[listener_id]

                # OPEN = HAProxy listener status nbconn < maxconn
                if listener.get('status') == constants.OPEN:
                    listener_status = constants.ONLINE
                # FULL = HAProxy listener status not nbconn < maxconn
                elif listener.get('status') == constants.FULL:
                    listener_status = constants.DEGRADED
                    if lb_status == constants.ONLINE:
                        lb_status = constants.DEGRADED
                else:
                    LOG.warning(('Listener %(list)s reported status of '
                                 '%(status)s'),
                                {'list': listener_id,
                                 'status': listener.get('status')})

            try:
                if (listener_status is not None and
                        listener_status != db_op_status):
                    self._update_status(
                        session, self.listener_repo, constants.LISTENER,
                        listener_id, listener_status, db_op_status)
            except sqlalchemy.orm.exc.NoResultFound:
                LOG.error("Listener %s is not in DB", listener_id)

            if not listener:
                continue

            if health_msg_version < 2:
                raw_pools = listener['pools']

                # normalize the pool IDs. Single process listener pools
                # have the listener id appended with an ':' seperator.
                # Old multi-process listener pools only have a pool ID.
                # This makes sure the keys are only pool IDs.
                pools = {(k + ' ')[:k.rfind(':')]: v for k, v in
                         raw_pools.items()}

                for db_pool_id in db_lb.get('pools', {}):
                    # If we saw this pool already on another listener, skip it.
                    if db_pool_id in processed_pools:
                        continue
                    db_pool_dict = db_lb['pools'][db_pool_id]
                    lb_status = self._process_pool_status(
                        session, db_pool_id, db_pool_dict, pools,
                        lb_status, processed_pools, potential_offline_pools)

        if health_msg_version >= 2:
            raw_pools = health['pools']

            # normalize the pool IDs. Single process listener pools
            # have the listener id appended with an ':' seperator.
            # Old multi-process listener pools only have a pool ID.
            # This makes sure the keys are only pool IDs.
            pools = {(k + ' ')[:k.rfind(':')]: v for k, v in raw_pools.items()}

            for db_pool_id in db_lb.get('pools', {}):
                # If we saw this pool already, skip it.
                if db_pool_id in processed_pools:
                    continue
                db_pool_dict = db_lb['pools'][db_pool_id]
                lb_status = self._process_pool_status(
                    session, db_pool_id, db_pool_dict, pools,
                    lb_status, processed_pools, potential_offline_pools)

        for pool_id in potential_offline_pools:
            # Skip if we eventually found a status for this pool
            if pool_id in processed_pools:
                continue
            try:
                # If the database doesn't already show the pool offline, update
                if potential_offline_pools[pool_id] != constants.OFFLINE:
                    self._update_status(
                        session, self.pool_repo, constants.POOL,
                        pool_id, constants.OFFLINE,
                        potential_offline_pools[pool_id])
            except sqlalchemy.orm.exc.NoResultFound:
                LOG.error("Pool %s is not in DB", pool_id)

        # Update the load balancer status last
        try:
            if lb_status != db_lb['operating_status']:
                self._update_status(
                    session, self.loadbalancer_repo,
                    constants.LOADBALANCER, db_lb['id'], lb_status,
                    db_lb[constants.OPERATING_STATUS])
        except sqlalchemy.orm.exc.NoResultFound:
            LOG.error("Load balancer %s is not in DB", db_lb.id)

    def _process_pool_status(
            self, session, pool_id, db_pool_dict, pools, lb_status,
            processed_pools, potential_offline_pools):
        pool_status = None

        if pool_id not in pools:
            # If we don't have a status update for this pool_id
            # add it to the list of potential offline pools and continue.
            # We will check the potential offline pool list after we
            # finish processing the status updates from all of the listeners.
            potential_offline_pools[pool_id] = db_pool_dict['operating_status']
            return lb_status

        pool = pools[pool_id]

        processed_pools.append(pool_id)

        # UP = HAProxy backend has working or no servers
        if pool.get('status') == constants.UP:
            pool_status = constants.ONLINE
        # DOWN = HAProxy backend has no working servers
        elif pool.get('status') == constants.DOWN:
            pool_status = constants.ERROR
            lb_status = constants.ERROR
        else:
            LOG.warning(('Pool %(pool)s reported status of '
                        '%(status)s'),
                        {'pool': pool_id,
                            'status': pool.get('status')})

        # Deal with the members that are reporting from
        # the Amphora
        members = pool['members']
        for member_id in db_pool_dict.get('members', {}):
            member_status = None
            member_db_status = (
                db_pool_dict['members'][member_id]['operating_status'])

            if member_id not in members:
                if member_db_status != constants.NO_MONITOR:
                    member_status = constants.OFFLINE
            else:
                status = members[member_id]

                # Member status can be "UP" or "UP #/#"
                # (transitional)
                if status.startswith(constants.UP):
                    member_status = constants.ONLINE
                # Member status can be "DOWN" or "DOWN #/#"
                # (transitional)
                elif status.startswith(constants.DOWN):
                    member_status = constants.ERROR
                    if pool_status == constants.ONLINE:
                        pool_status = constants.DEGRADED
                        if lb_status == constants.ONLINE:
                            lb_status = constants.DEGRADED
                elif status == constants.DRAIN:
                    member_status = constants.DRAINING
                elif status == constants.MAINT:
                    member_status = constants.OFFLINE
                elif status == constants.NO_CHECK:
                    member_status = constants.NO_MONITOR
                else:
                    LOG.warning('Member %(mem)s reported '
                                'status of %(status)s',
                                {'mem': member_id,
                                    'status': status})

            try:
                if (member_status is not None and
                        member_status != member_db_status):
                    self._update_status(
                        session, self.member_repo, constants.MEMBER,
                        member_id, member_status, member_db_status)
            except sqlalchemy.orm.exc.NoResultFound:
                LOG.error("Member %s is not able to update "
                          "in DB", member_id)

        try:
            if (pool_status is not None and
                    pool_status != db_pool_dict['operating_status']):
                self._update_status(
                    session, self.pool_repo, constants.POOL,
                    pool_id, pool_status, db_pool_dict['operating_status'])
        except sqlalchemy.orm.exc.NoResultFound:
            LOG.error("Pool %s is not in DB", pool_id)

        return lb_status


class UpdateStatsDb(update_base.StatsUpdateBase, stats.StatsMixin):

    def __init__(self):
        super(UpdateStatsDb, self).__init__()
        self.repo_listener = repo.ListenerRepository()

    def update_stats(self, health_message, srcaddr):
        # The executor will eat any exceptions from the update_stats code
        # so we need to wrap it and log the unhandled exception
        try:
            self._update_stats(health_message, srcaddr)
        except Exception:
            LOG.exception('update_stats encountered an unknown error '
                          'processing stats for amphora %s with IP '
                          '%s', health_message['id'], srcaddr)

    def _update_stats(self, health_message, srcaddr):
        """This function is to update the db with listener stats

        :param health_message: The health message containing the listener stats
        :type map: string
        :returns: null

        Example V1 message::

            health = {
                "id": self.FAKE_UUID_1,
                "listeners": {
                    "listener-id-1": {
                        "status": constants.OPEN,
                        "stats": {
                            "ereq":0,
                            "conns": 0,
                            "totconns": 0,
                            "rx": 0,
                            "tx": 0,
                        },
                        "pools": {
                            "pool-id-1": {
                                "status": constants.UP,
                                "members": {"member-id-1": constants.ONLINE}
                            }
                        }
                    }
                }
            }

        Example V2 message::

            {"id": "<amphora_id>",
             "seq": 67,
             "listeners": {
               "<listener_id>": {
                 "status": "OPEN",
                 "stats": {
                   "tx": 0,
                   "rx": 0,
                   "conns": 0,
                   "totconns": 0,
                   "ereq": 0
                 }
               }
             },
             "pools": {
                 "<pool_id>:<listener_id>": {
                   "status": "UP",
                   "members": {
                     "<member_id>": "no check"
                   }
                 }
             },
             "ver": 2
            }

        """
        session = db_api.get_session()

        amphora_id = health_message['id']
        listeners = health_message['listeners']
        for listener_id, listener in listeners.items():

            stats = listener.get('stats')
            stats = {'bytes_in': stats['rx'], 'bytes_out': stats['tx'],
                     'active_connections': stats['conns'],
                     'total_connections': stats['totconns'],
                     'request_errors': stats['ereq']}
            LOG.debug("Updating listener stats in db and sending event.")
            LOG.debug("Listener %s / Amphora %s stats: %s",
                      listener_id, amphora_id, stats)
            self.listener_stats_repo.replace(
                session, listener_id, amphora_id, **stats)
