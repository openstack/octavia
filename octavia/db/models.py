#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
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

from oslo_db.sqlalchemy import models
import sqlalchemy as sa
from sqlalchemy.ext import orderinglist
from sqlalchemy import orm
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from octavia.api.v2.types import health_monitor
from octavia.api.v2.types import l7policy
from octavia.api.v2.types import l7rule
from octavia.api.v2.types import listener
from octavia.api.v2.types import load_balancer
from octavia.api.v2.types import member
from octavia.api.v2.types import pool
from octavia.api.v2.types import quotas
from octavia.common import data_models
from octavia.db import base_models


class ProvisioningStatus(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "provisioning_status"


class OperatingStatus(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "operating_status"


class Protocol(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "protocol"


class Algorithm(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "algorithm"


class AmphoraRoles(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "amphora_roles"


class LBTopology(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "lb_topology"


class SessionPersistenceType(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "session_persistence_type"


class HealthMonitorType(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "health_monitor_type"


class VRRPAuthMethod(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "vrrp_auth_method"


class L7RuleType(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "l7rule_type"


class L7RuleCompareType(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "l7rule_compare_type"


class L7PolicyAction(base_models.BASE, base_models.LookupTableMixin):

    __tablename__ = "l7policy_action"


class AmphoraBuildSlots(base_models.BASE):

    __tablename__ = "amphora_build_slots"

    id = sa.Column(sa.Integer(), primary_key=True)
    slots_used = sa.Column(sa.Integer())


class AmphoraBuildRequest(base_models.BASE):

    __tablename__ = "amphora_build_request"

    amphora_id = sa.Column(sa.String(36), nullable=True, primary_key=True)
    priority = sa.Column(sa.Integer())
    created_time = sa.Column(sa.DateTime, default=func.now(), nullable=False)
    status = sa.Column(sa.String(16), default='WAITING', nullable=False)


class SessionPersistence(base_models.BASE):

    __data_model__ = data_models.SessionPersistence

    __tablename__ = "session_persistence"

    pool_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("pool.id", name="fk_session_persistence_pool_id"),
        nullable=False,
        primary_key=True)
    type = sa.Column(
        sa.String(36),
        sa.ForeignKey(
            "session_persistence_type.name",
            name="fk_session_persistence_session_persistence_type_name"),
        nullable=False)
    cookie_name = sa.Column(sa.String(255), nullable=True)
    pool = orm.relationship("Pool", uselist=False,
                            backref=orm.backref("session_persistence",
                                                uselist=False,
                                                cascade="delete"))


class ListenerStatistics(base_models.BASE):

    __data_model__ = data_models.ListenerStatistics

    __tablename__ = "listener_statistics"

    listener_id = sa.Column(
        sa.String(36),
        primary_key=True,
        nullable=False)
    amphora_id = sa.Column(
        sa.String(36),
        primary_key=True,
        nullable=False)
    bytes_in = sa.Column(sa.BigInteger, nullable=False)
    bytes_out = sa.Column(sa.BigInteger, nullable=False)
    active_connections = sa.Column(sa.Integer, nullable=False)
    total_connections = sa.Column(sa.BigInteger, nullable=False)
    request_errors = sa.Column(sa.BigInteger, nullable=False)

    @validates('bytes_in', 'bytes_out',
               'active_connections', 'total_connections',
               'request_errors')
    def validate_non_negative_int(self, key, value):
        if value < 0:
            data = {'key': key, 'value': value}
            raise ValueError(_('The %(key)s field can not have '
                               'negative value. '
                               'Current value is %(value)d.') % data)
        return value


class Member(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
             models.TimestampMixin, base_models.NameMixin):

    __data_model__ = data_models.Member

    __tablename__ = "member"

    __v2_wsme__ = member.MemberResponse

    __table_args__ = (
        sa.UniqueConstraint('pool_id', 'ip_address', 'protocol_port',
                            name='uq_member_pool_id_address_protocol_port'),
    )

    pool_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("pool.id", name="fk_member_pool_id"),
        nullable=False)
    subnet_id = sa.Column(sa.String(36), nullable=True)
    ip_address = sa.Column('ip_address', sa.String(64), nullable=False)
    protocol_port = sa.Column(sa.Integer, nullable=False)
    weight = sa.Column(sa.Integer, nullable=True)
    monitor_address = sa.Column(sa.String(64), nullable=True)
    monitor_port = sa.Column(sa.Integer, nullable=True)
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_member_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_member_operating_status_name"),
        nullable=False)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    pool = orm.relationship("Pool", backref=orm.backref("members",
                                                        uselist=True,
                                                        cascade="delete"))


class HealthMonitor(base_models.BASE, base_models.IdMixin,
                    base_models.ProjectMixin, models.TimestampMixin,
                    base_models.NameMixin):

    __data_model__ = data_models.HealthMonitor

    __tablename__ = "health_monitor"

    __v2_wsme__ = health_monitor.HealthMonitorResponse

    type = sa.Column(
        sa.String(36),
        sa.ForeignKey("health_monitor_type.name",
                      name="fk_health_monitor_health_monitor_type_name"),
        nullable=False)
    pool_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("pool.id", name="fk_health_monitor_pool_id"),
        nullable=False)
    delay = sa.Column(sa.Integer, nullable=False)
    timeout = sa.Column(sa.Integer, nullable=False)
    fall_threshold = sa.Column(sa.Integer, nullable=False)
    rise_threshold = sa.Column(sa.Integer, nullable=False)
    http_method = sa.Column(sa.String(16), nullable=True)
    url_path = sa.Column(sa.String(2048), nullable=True)
    expected_codes = sa.Column(sa.String(64), nullable=True)
    enabled = sa.Column(sa.Boolean, nullable=False)
    pool = orm.relationship("Pool", uselist=False,
                            backref=orm.backref("health_monitor",
                                                uselist=False,
                                                cascade="delete"))
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_health_monitor_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_health_monitor_operating_status_name"),
        nullable=False)


class Pool(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
           models.TimestampMixin, base_models.NameMixin):

    __data_model__ = data_models.Pool

    __tablename__ = "pool"

    __v2_wsme__ = pool.PoolResponse

    description = sa.Column(sa.String(255), nullable=True)
    protocol = sa.Column(
        sa.String(16),
        sa.ForeignKey("protocol.name", name="fk_pool_protocol_name"),
        nullable=False)
    lb_algorithm = sa.Column(
        sa.String(255),
        sa.ForeignKey("algorithm.name", name="fk_pool_algorithm_name"),
        nullable=False)
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_pool_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_pool_operating_status_name"),
        nullable=False)
    enabled = sa.Column(sa.Boolean, nullable=False)
    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("load_balancer.id", name="fk_pool_load_balancer_id"),
        nullable=True)
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     backref=orm.backref("pools",
                                                         uselist=True,
                                                         cascade="delete"))

    # This property should be a unique list of any listeners that reference
    # this pool as its default_pool and any listeners referenced by enabled
    # L7Policies with at least one l7rule which also reference this pool. The
    # intent is that pool.listeners should be a unique list of listeners
    # *actually* using the pool.
    @property
    def listeners(self):
        _listeners = self._default_listeners[:]
        _l_ids = [l.id for l in _listeners]
        l7_listeners = [p.listener for p in self.l7policies
                        if len(p.l7rules) > 0 and p.enabled is True]
        for l in l7_listeners:
            if l.id not in _l_ids:
                _listeners.append(l)
                _l_ids.append(l.id)
        return _listeners


class LoadBalancer(base_models.BASE, base_models.IdMixin,
                   base_models.ProjectMixin, models.TimestampMixin,
                   base_models.NameMixin):

    __data_model__ = data_models.LoadBalancer

    __tablename__ = "load_balancer"

    __v2_wsme__ = load_balancer.LoadBalancerResponse

    description = sa.Column(sa.String(255), nullable=True)
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_load_balancer_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_load_balancer_operating_status_name"),
        nullable=False)
    topology = sa.Column(
        sa.String(36),
        sa.ForeignKey("lb_topology.name", name="fk_lb_topology_name"),
        nullable=True)
    enabled = sa.Column(sa.Boolean, nullable=False)
    amphorae = orm.relationship("Amphora", uselist=True,
                                backref=orm.backref("load_balancer",
                                                    uselist=False))
    server_group_id = sa.Column(sa.String(36), nullable=True)


class VRRPGroup(base_models.BASE):

    __data_model__ = data_models.VRRPGroup

    __tablename__ = "vrrp_group"

    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("load_balancer.id",
                      name="fk_vrrp_group_load_balancer_id"),
        nullable=False, primary_key=True)

    vrrp_group_name = sa.Column(sa.String(36), nullable=True)
    vrrp_auth_type = sa.Column(sa.String(16), sa.ForeignKey(
        "vrrp_auth_method.name",
        name="fk_load_balancer_vrrp_auth_method_name"))
    vrrp_auth_pass = sa.Column(sa.String(36), nullable=True)
    advert_int = sa.Column(sa.Integer(), nullable=True)
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     backref=orm.backref("vrrp_group",
                                                         uselist=False,
                                                         cascade="delete"))


class Vip(base_models.BASE):

    __data_model__ = data_models.Vip

    __tablename__ = "vip"

    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("load_balancer.id",
                      name="fk_vip_load_balancer_id"),
        nullable=False, primary_key=True)
    ip_address = sa.Column(sa.String(64), nullable=True)
    port_id = sa.Column(sa.String(36), nullable=True)
    subnet_id = sa.Column(sa.String(36), nullable=True)
    network_id = sa.Column(sa.String(36), nullable=True)
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     backref=orm.backref("vip", uselist=False,
                                                         cascade="delete"))


class Listener(base_models.BASE, base_models.IdMixin,
               base_models.ProjectMixin, models.TimestampMixin,
               base_models.NameMixin):

    __data_model__ = data_models.Listener

    __tablename__ = "listener"

    __v2_wsme__ = listener.ListenerResponse

    __table_args__ = (
        sa.UniqueConstraint('load_balancer_id', 'protocol_port',
                            name='uq_listener_load_balancer_id_protocol_port'),
    )

    description = sa.Column(sa.String(255), nullable=True)
    protocol = sa.Column(
        sa.String(16),
        sa.ForeignKey("protocol.name", name="fk_listener_protocol_name"),
        nullable=False)
    protocol_port = sa.Column(sa.Integer(), nullable=False)
    connection_limit = sa.Column(sa.Integer, nullable=True)
    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("load_balancer.id", name="fk_listener_load_balancer_id"),
        nullable=True)
    tls_certificate_id = sa.Column(sa.String(36), nullable=True)
    default_pool_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("pool.id", name="fk_listener_pool_id"),
        nullable=True)
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_listener_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_listener_operating_status_name"),
        nullable=False)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     backref=orm.backref("listeners",
                                                         uselist=True,
                                                         cascade="delete"))
    default_pool = orm.relationship("Pool", uselist=False,
                                    backref=orm.backref("_default_listeners",
                                                        uselist=True))

    peer_port = sa.Column(sa.Integer(), nullable=True)
    insert_headers = sa.Column(sa.PickleType())

    # This property should be a unique list of the default_pool and anything
    # referenced by enabled L7Policies with at least one rule that also
    # reference this listener. The intent is that listener.pools should be a
    # unique list of pools this listener is *actually* using.
    @property
    def pools(self):
        _pools = []
        _p_ids = []
        if self.default_pool:
            _pools.append(self.default_pool)
            _p_ids.append(self.default_pool.id)
        l7_pools = [p.redirect_pool for p in self.l7policies
                    if p.redirect_pool is not None and len(p.l7rules) > 0 and
                    p.enabled is True]
        for p in l7_pools:
            if p.id not in _p_ids:
                _pools.append(p)
                _p_ids.append(p.id)
        return _pools


class SNI(base_models.BASE):

    __data_model__ = data_models.SNI

    __tablename__ = "sni"
    __table_args__ = (
        sa.PrimaryKeyConstraint('listener_id', 'tls_container_id'),
    )

    listener_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("listener.id", name="fk_sni_listener_id"),
        nullable=False)
    tls_container_id = sa.Column(sa.String(128), nullable=False)
    position = sa.Column(sa.Integer(), nullable=True)
    listener = orm.relationship("Listener", uselist=False,
                                backref=orm.backref("sni_containers",
                                                    uselist=True,
                                                    cascade="delete"))


class Amphora(base_models.BASE, base_models.IdMixin):

    __data_model__ = data_models.Amphora

    __tablename__ = "amphora"

    load_balancer_id = sa.Column(
        sa.String(36), sa.ForeignKey("load_balancer.id",
                                     name="fk_amphora_load_balancer_id"),
        nullable=True)
    compute_id = sa.Column(sa.String(36), nullable=True)
    lb_network_ip = sa.Column(sa.String(64), nullable=True)
    vrrp_ip = sa.Column(sa.String(64), nullable=True)
    ha_ip = sa.Column(sa.String(64), nullable=True)
    vrrp_port_id = sa.Column(sa.String(36), nullable=True)
    ha_port_id = sa.Column(sa.String(36), nullable=True)
    cert_expiration = sa.Column(sa.DateTime(timezone=True), default=None,
                                nullable=True)
    cert_busy = sa.Column(sa.Boolean(), default=False, nullable=False)

    role = sa.Column(
        sa.String(36),
        sa.ForeignKey("amphora_roles.name", name="fk_amphora_roles_name"),
        nullable=True)
    status = sa.Column(
        sa.String(36),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_container_provisioning_status_name"))
    vrrp_interface = sa.Column(sa.String(16), nullable=True)
    vrrp_id = sa.Column(sa.Integer(), nullable=True)
    vrrp_priority = sa.Column(sa.Integer(), nullable=True)


class AmphoraHealth(base_models.BASE):
    __data_model__ = data_models.AmphoraHealth
    __tablename__ = "amphora_health"

    amphora_id = sa.Column(
        sa.String(36), nullable=False, primary_key=True)
    last_update = sa.Column(sa.DateTime, default=func.now(),
                            nullable=False)

    busy = sa.Column(sa.Boolean(), default=False, nullable=False)


class L7Rule(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
             models.TimestampMixin):

    __data_model__ = data_models.L7Rule

    __tablename__ = "l7rule"

    __v2_wsme__ = l7rule.L7RuleResponse

    l7policy_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("l7policy.id", name="fk_l7rule_l7policy_id"),
        nullable=False)
    type = sa.Column(
        sa.String(36),
        sa.ForeignKey(
            "l7rule_type.name",
            name="fk_l7rule_l7rule_type_name"),
        nullable=False)
    compare_type = sa.Column(
        sa.String(36),
        sa.ForeignKey(
            "l7rule_compare_type.name",
            name="fk_l7rule_l7rule_compare_type_name"),
        nullable=False)
    key = sa.Column(sa.String(255), nullable=True)
    value = sa.Column(sa.String(255), nullable=False)
    invert = sa.Column(sa.Boolean(), default=False, nullable=False)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    l7policy = orm.relationship("L7Policy", uselist=False,
                                backref=orm.backref("l7rules",
                                                    uselist=True,
                                                    cascade="delete"))
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_l7rule_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_l7rule_operating_status_name"),
        nullable=False)


class L7Policy(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
               models.TimestampMixin, base_models.NameMixin):

    __data_model__ = data_models.L7Policy

    __tablename__ = "l7policy"

    __v2_wsme__ = l7policy.L7PolicyResponse

    description = sa.Column(sa.String(255), nullable=True)
    listener_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("listener.id", name="fk_l7policy_listener_id"),
        nullable=False)
    action = sa.Column(
        sa.String(36),
        sa.ForeignKey(
            "l7policy_action.name",
            name="fk_l7policy_l7policy_action_name"),
        nullable=False)
    redirect_pool_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("pool.id", name="fk_l7policy_pool_id"),
        nullable=True)
    redirect_url = sa.Column(
        sa.String(255),
        nullable=True)
    position = sa.Column(sa.Integer, nullable=False)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    listener = orm.relationship(
        "Listener", uselist=False,
        backref=orm.backref(
            "l7policies",
            uselist=True,
            order_by="L7Policy.position",
            collection_class=orderinglist.ordering_list('position',
                                                        count_from=1),
            cascade="delete"))
    redirect_pool = orm.relationship("Pool", uselist=False,
                                     backref=orm.backref("l7policies",
                                                         uselist=True))
    provisioning_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("provisioning_status.name",
                      name="fk_l7policy_provisioning_status_name"),
        nullable=False)
    operating_status = sa.Column(
        sa.String(16),
        sa.ForeignKey("operating_status.name",
                      name="fk_l7policy_operating_status_name"),
        nullable=False)


class Quotas(base_models.BASE):

    __data_model__ = data_models.Quotas

    __tablename__ = "quotas"

    __v2_wsme__ = quotas.QuotaAllBase

    project_id = sa.Column(sa.String(36), primary_key=True)
    health_monitor = sa.Column(sa.Integer(), nullable=True)
    listener = sa.Column(sa.Integer(), nullable=True)
    load_balancer = sa.Column(sa.Integer(), nullable=True)
    member = sa.Column(sa.Integer(), nullable=True)
    pool = sa.Column(sa.Integer(), nullable=True)
    in_use_health_monitor = sa.Column(sa.Integer(), nullable=True)
    in_use_listener = sa.Column(sa.Integer(), nullable=True)
    in_use_load_balancer = sa.Column(sa.Integer(), nullable=True)
    in_use_member = sa.Column(sa.Integer(), nullable=True)
    in_use_pool = sa.Column(sa.Integer(), nullable=True)
