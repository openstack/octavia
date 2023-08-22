# Copyright 2014 Rackspace
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

from concurrent import futures
import datetime
import socket
import time
import timeit

from oslo_config import cfg
from oslo_log import log as logging
from oslo_utils import excutils
import sqlalchemy
from stevedore import driver as stevedore_driver

from octavia.amphorae.backends.health_daemon import status_message
from octavia.common import constants
from octavia.common import data_models
from octavia.common import exceptions
from octavia.db import api as db_api
from octavia.db import repositories as repo
from octavia.statistics import stats_base

UDP_MAX_SIZE = 64 * 1024
CONF = cfg.CONF
LOG = logging.getLogger(__name__)


class UDPStatusGetter(object):
    """This class defines methods that will gather heartbeats

    The heartbeats are transmitted via UDP and this class will bind to a port
    and absorb them
    """
    def __init__(self):
        self.key = cfg.CONF.health_manager.heartbeat_key
        self.ip = cfg.CONF.health_manager.bind_ip
        self.port = cfg.CONF.health_manager.bind_port
        self.sockaddr = None
        LOG.info('attempting to listen on %(ip)s port %(port)s',
                 {'ip': self.ip, 'port': self.port})
        self.sock = None
        self.update(self.key, self.ip, self.port)

        self.health_executor = futures.ProcessPoolExecutor(
            max_workers=CONF.health_manager.health_update_threads)
        self.stats_executor = futures.ProcessPoolExecutor(
            max_workers=CONF.health_manager.stats_update_threads)
        self.health_updater = UpdateHealthDb()

    def update(self, key, ip, port):
        """Update the running config for the udp socket server

        :param key: The hmac key used to verify the UDP packets. String
        :param ip: The ip address the UDP server will read from
        :param port: The port the UDP server will read from
        :return: None
        """
        self.key = key
        for addrinfo in socket.getaddrinfo(ip, port, 0, socket.SOCK_DGRAM):
            ai_family = addrinfo[0]
            self.sockaddr = addrinfo[4]
            if self.sock is not None:
                self.sock.close()
            self.sock = socket.socket(ai_family, socket.SOCK_DGRAM)
            self.sock.settimeout(1)
            self.sock.bind(self.sockaddr)
            if cfg.CONF.health_manager.sock_rlimit > 0:
                rlimit = cfg.CONF.health_manager.sock_rlimit
                LOG.info("setting sock rlimit to %s", rlimit)
                self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF,
                                     rlimit)
            break  # just used the first addr getaddrinfo finds
        if self.sock is None:
            raise exceptions.NetworkConfig("unable to find suitable socket")

    def dorecv(self, *args, **kw):
        """Waits for a UDP heart beat to be sent.

        :return: Returns the unwrapped payload and addr that sent the
                 heartbeat.
        """
        (data, srcaddr) = self.sock.recvfrom(UDP_MAX_SIZE)
        LOG.debug('Received packet from %s', srcaddr)
        try:
            obj = status_message.unwrap_envelope(data, self.key)
        except Exception as e:
            LOG.warning('Health Manager experienced an exception processing a '
                        'heartbeat message from %s. Ignoring this packet. '
                        'Exception: %s', srcaddr, str(e))
            raise exceptions.InvalidHMACException()
        obj['recv_time'] = time.time()
        return obj, srcaddr[0]

    def check(self):
        try:
            obj, srcaddr = self.dorecv()
        except socket.timeout:
            # Pass here as this is an expected cycling of the listen socket
            pass
        except exceptions.InvalidHMACException:
            # Pass here as the packet was dropped and logged already
            pass
        except Exception as e:
            LOG.warning('Health Manager experienced an exception processing a '
                        'heartbeat packet. Ignoring this packet. '
                        'Exception: %s', str(e))
        else:
            self.health_executor.submit(self.health_updater.update_health,
                                        obj, srcaddr)
            self.stats_executor.submit(update_stats, obj)


def update_stats(health_message):
    """Parses the health message then passes it to the stats driver(s)

    :param health_message: The health message containing the listener stats
    :type health_message: dict

    Example V1 message::

        health = {
            "id": "<amphora_id>",
            "listeners": {
                "<listener_id>": {
                    "status": "OPEN",
                    "stats": {
                        "ereq": 0,
                        "conns": 0,
                        "totconns": 0,
                        "rx": 0,
                        "tx": 0,
                    },
                    "pools": {
                        "<pool_id>": {
                            "status": "UP",
                            "members": {"<member_id>": "ONLINE"}
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
         "recv_time": time.time()
        }

    Example V3 message::

        Same as V2 message, except values are deltas rather than absolutes.
    """
    version = health_message.get("ver", 2)

    deltas = False
    if version >= 3:
        deltas = True

    amphora_id = health_message.get('id')
    listeners = health_message.get('listeners', {})
    listener_stats = []
    for listener_id, listener in listeners.items():
        listener_dict = listener.get('stats')
        stats_model = data_models.ListenerStatistics(
            listener_id=listener_id,
            amphora_id=amphora_id,
            bytes_in=listener_dict.get('rx'),
            bytes_out=listener_dict.get('tx'),
            active_connections=listener_dict.get('conns'),
            total_connections=listener_dict.get('totconns'),
            request_errors=listener_dict.get('ereq'),
            received_time=health_message.get('recv_time')
        )
        LOG.debug("Listener %s / Amphora %s stats: %s",
                  listener_id, amphora_id, stats_model.get_stats())
        listener_stats.append(stats_model)
    stats_base.update_stats_via_driver(listener_stats, deltas=deltas)


class UpdateHealthDb:
    def __init__(self):
        super().__init__()
        # first setup repo for amphora, listener,member(nodes),pool repo
        self.amphora_repo = repo.AmphoraRepository()
        self.amphora_health_repo = repo.AmphoraHealthRepository()
        self.listener_repo = repo.ListenerRepository()
        self.loadbalancer_repo = repo.LoadBalancerRepository()
        self.member_repo = repo.MemberRepository()
        self.pool_repo = repo.PoolRepository()

    @staticmethod
    def _update_status(session, repo, entity_type,
                       entity_id, new_op_status, old_op_status):
        if old_op_status.lower() != new_op_status.lower():
            LOG.debug("%s %s status has changed from %s to "
                      "%s, updating db.",
                      entity_type, entity_id, old_op_status,
                      new_op_status)
            repo.update(session, entity_id, operating_status=new_op_status)

    def update_health(self, health, srcaddr):
        # The executor will eat any exceptions from the update_health code
        # so we need to wrap it and log the unhandled exception
        start_time = timeit.default_timer()
        try:
            self._update_health(health, srcaddr)
        except Exception as e:
            LOG.exception('Health update for amphora %(amp)s encountered '
                          'error %(err)s. Skipping health update.',
                          {'amp': health['id'], 'err': str(e)})
        # TODO(johnsom) We need to set a warning threshold here
        LOG.debug('Health Update finished in: %s seconds',
                  timeit.default_timer() - start_time)

    # Health heartbeat message pre-versioning with UDP listeners
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
        with session.begin():
            db_lb = self.amphora_repo.get_lb_for_health_update(session,
                                                               health['id'])
        ignore_listener_count = False

        if db_lb:
            expected_listener_count = 0
            if ('PENDING' in db_lb['provisioning_status'] or
               not db_lb['enabled']):
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
                        with session.begin():
                            expected_listener_count = (
                                self._update_listener_count_for_UDP(
                                    session, db_lb, expected_listener_count))
        else:
            with session.begin():
                amp = self.amphora_repo.get(session, id=health['id'])
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
                         health['id'], srcaddr, str(e))
            expected_listener_count = 0

        listeners = health['listeners']

        # Do not update amphora health if the reporting listener count
        # does not match the expected listener count
        if len(listeners) == expected_listener_count or ignore_listener_count:

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

            lock_session = db_api.get_session()
            lock_session.begin()

            # if the input amphora is healthy, we update its db info
            try:
                self.amphora_health_repo.replace(
                    lock_session, health['id'],
                    last_update=datetime.datetime.utcnow())
                lock_session.commit()
            except Exception:
                with excutils.save_and_reraise_exception():
                    lock_session.rollback()
        else:
            LOG.warning('Amphora %(id)s health message reports %(found)i '
                        'listeners when %(expected)i expected',
                        {'id': health['id'], 'found': len(listeners),
                         'expected': expected_listener_count})

        # Don't try to update status for bogus or old spares pool amphora
        if not db_lb:
            return

        processed_pools = []
        potential_offline_pools = {}

        # We got a heartbeat so lb is healthy until proven otherwise
        if db_lb[constants.ENABLED] is False:
            lb_status = constants.OFFLINE
        else:
            lb_status = constants.ONLINE

        health_msg_version = health.get('ver', 0)

        for listener_id in db_lb.get(constants.LISTENERS, {}):
            db_listener = db_lb[constants.LISTENERS][listener_id]
            db_op_status = db_listener[constants.OPERATING_STATUS]
            listener_status = None
            listener = None

            if listener_id not in listeners:
                if (db_listener[constants.ENABLED] and
                    db_lb[constants.PROVISIONING_STATUS] ==
                        constants.ACTIVE):
                    listener_status = constants.ERROR
                else:
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
                    with session.begin():
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
                    with session.begin():
                        lb_status = self._process_pool_status(
                            session, db_pool_id, db_pool_dict, pools,
                            lb_status, processed_pools,
                            potential_offline_pools)

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
                with session.begin():
                    lb_status = self._process_pool_status(
                        session, db_pool_id, db_pool_dict, pools,
                        lb_status, processed_pools, potential_offline_pools)

        for pool_id, pool in potential_offline_pools.items():
            # Skip if we eventually found a status for this pool
            if pool_id in processed_pools:
                continue
            try:
                # If the database doesn't already show the pool offline, update
                if pool != constants.OFFLINE:
                    with session.begin():
                        self._update_status(
                            session, self.pool_repo, constants.POOL,
                            pool_id, constants.OFFLINE, pool)
            except sqlalchemy.orm.exc.NoResultFound:
                LOG.error("Pool %s is not in DB", pool_id)

        # Update the load balancer status last
        try:
            if lb_status != db_lb['operating_status']:
                with session.begin():
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
                elif status == constants.RESTARTING:
                    # RESTARTING means that keepalived is restarting and a down
                    # member has been detected, the real status of the member
                    # is not clear, it might mean that the checker hasn't run
                    # yet.
                    # In this case, keep previous member_status, and wait for a
                    # non-transitional status.
                    pass
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
