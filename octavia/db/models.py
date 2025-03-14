#    Copyright 2014 Rackspace
#    Copyright 2016 Blue Box, an IBM Company
#    Copyright 2017 Walmart Stores Inc.
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
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import validates
from sqlalchemy.sql import func
from sqlalchemy_utils import ScalarListType

from octavia.api.v2.types import amphora
from octavia.api.v2.types import availability_zone_profile
from octavia.api.v2.types import availability_zones
from octavia.api.v2.types import flavor_profile
from octavia.api.v2.types import flavors
from octavia.api.v2.types import health_monitor
from octavia.api.v2.types import l7policy
from octavia.api.v2.types import l7rule
from octavia.api.v2.types import listener
from octavia.api.v2.types import load_balancer
from octavia.api.v2.types import member
from octavia.api.v2.types import pool
from octavia.api.v2.types import quotas
from octavia.common import constants
from octavia.common import data_models
from octavia.db import base_models
from octavia.i18n import _


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
    persistence_timeout = sa.Column(sa.Integer(), nullable=True)
    persistence_granularity = sa.Column(sa.String(64), nullable=True)
    pool = orm.relationship("Pool", uselist=False,
                            back_populates="session_persistence")


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

    def __iadd__(self, other):
        if isinstance(other, (ListenerStatistics,
                              data_models.ListenerStatistics)):
            self.bytes_in += other.bytes_in
            self.bytes_out += other.bytes_out
            self.request_errors += other.request_errors
            self.total_connections += other.total_connections
        else:
            raise TypeError(  # noqa: O342
                "unsupported operand type(s) for +=: '{}' and '{}'".format(
                    type(self), type(other)))

        return self


class Member(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
             models.TimestampMixin, base_models.NameMixin,
             base_models.TagMixin):

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
    backup = sa.Column(sa.Boolean(), nullable=False)
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
    pool = orm.relationship("Pool", back_populates="members")
    vnic_type = sa.Column(sa.String(64), nullable=True)

    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==Member.id)',
        overlaps='_tags'
    )

    def __str__(self):
        return (f"Member(id={self.id!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, "
                f"provisioning_status={self.provisioning_status!r}, "
                f"ip_address={self.ip_address!r}, "
                f"protocol_port={self.protocol_port!r}, "
                f"operating_status={self.operating_status!r}, "
                f"weight={self.weight!r}, vnic_type={self.vnic_type!r})")


class HealthMonitor(base_models.BASE, base_models.IdMixin,
                    base_models.ProjectMixin, models.TimestampMixin,
                    base_models.NameMixin, base_models.TagMixin):

    __data_model__ = data_models.HealthMonitor

    __tablename__ = "health_monitor"

    __v2_wsme__ = health_monitor.HealthMonitorResponse

    __table_args__ = (
        sa.UniqueConstraint('pool_id',
                            name='uq_health_monitor_pool'),
    )

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
                            back_populates="health_monitor")

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
    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==HealthMonitor.id)',
        overlaps='_tags'
    )
    http_version = sa.Column(sa.Float, nullable=True)
    domain_name = sa.Column(sa.String(255), nullable=True)

    def __str__(self):
        return (f"HealthMonitor(id={self.id!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, type={self.type!r}, "
                f"enabled={self.enabled!r})")


class Pool(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
           models.TimestampMixin, base_models.NameMixin, base_models.TagMixin):

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
    health_monitor = orm.relationship("HealthMonitor", uselist=False,
                                      cascade="delete", back_populates="pool")
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     back_populates="pools")
    members = orm.relationship("Member", uselist=True, cascade="delete",
                               back_populates="pool")
    session_persistence = orm.relationship(
        "SessionPersistence", uselist=False, cascade="delete",
        back_populates="pool")
    _default_listeners = orm.relationship("Listener", uselist=True,
                                          back_populates="default_pool",
                                          cascade_backrefs=False)
    l7policies = orm.relationship("L7Policy", uselist=True,
                                  back_populates="redirect_pool")
    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==Pool.id)',
        overlaps='_tags'
    )
    tls_certificate_id = sa.Column(sa.String(255), nullable=True)
    ca_tls_certificate_id = sa.Column(sa.String(255), nullable=True)
    crl_container_id = sa.Column(sa.String(255), nullable=True)
    tls_enabled = sa.Column(sa.Boolean, default=False, nullable=False)
    tls_ciphers = sa.Column(sa.String(2048), nullable=True)
    tls_versions = sa.Column(ScalarListType(), nullable=True)
    alpn_protocols = sa.Column(ScalarListType(), nullable=True)

    # This property should be a unique list of any listeners that reference
    # this pool as its default_pool and any listeners referenced by enabled
    # L7Policies with at least one l7rule which also reference this pool. The
    # intent is that pool.listeners should be a unique list of listeners
    # *actually* using the pool.
    @property
    def listeners(self):
        _listeners = self._default_listeners[:]
        _l_ids = [li.id for li in _listeners]
        l7_listeners = [p.listener for p in self.l7policies
                        if len(p.l7rules) > 0 and p.enabled is True]
        for li in l7_listeners:
            if li.id not in _l_ids:
                _listeners.append(li)
                _l_ids.append(li.id)
        return _listeners

    def __str__(self):
        return (f"Pool(id={self.id!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, "
                f"provisioning_status={self.provisioning_status!r}, "
                f"protocol={self.protocol!r}, "
                f"lb_algorithm={self.lb_algorithm!r}, "
                f"enabled={self.enabled!r})")


class LoadBalancer(base_models.BASE, base_models.IdMixin,
                   base_models.ProjectMixin, models.TimestampMixin,
                   base_models.NameMixin, base_models.TagMixin):

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
                                back_populates="load_balancer")
    server_group_id = sa.Column(sa.String(36), nullable=True)
    provider = sa.Column(sa.String(64), nullable=True)
    vip = orm.relationship('Vip', cascade='delete', uselist=False,
                           backref=orm.backref('load_balancer', uselist=False))
    additional_vips = orm.relationship(
        'AdditionalVip', cascade='delete', uselist=True,
        backref=orm.backref('load_balancer', uselist=False))
    pools = orm.relationship('Pool', cascade='delete', uselist=True,
                             back_populates="load_balancer")
    listeners = orm.relationship('Listener', cascade='delete', uselist=True,
                                 back_populates='load_balancer')
    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==LoadBalancer.id)',
        overlaps='_tags'
    )
    flavor_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("flavor.id", name="fk_lb_flavor_id"), nullable=True)
    availability_zone = sa.Column(
        sa.String(255),
        sa.ForeignKey("availability_zone.name",
                      name="fk_load_balancer_availability_zone_name"),
        nullable=True)
    flavor: Mapped["Flavor"] = orm.relationship("Flavor")

    def __str__(self):
        return (f"LoadBalancer(id={self.id!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, vip={self.vip!r}, "
                f"provisioning_status={self.provisioning_status!r}, "
                f"operating_status={self.operating_status!r}, "
                f"provider={self.provider!r})")


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
    qos_policy_id = sa.Column(sa.String(36), nullable=True)
    octavia_owned = sa.Column(sa.Boolean(), nullable=True)
    vnic_type = sa.Column(sa.String(64), nullable=True)

    sgs = orm.relationship(
        "VipSecurityGroup", cascade="all,delete-orphan",
        uselist=True, backref=orm.backref("vip", uselist=False))

    @property
    def sg_ids(self) -> list[str]:
        return [sg.sg_id for sg in self.sgs]


class AdditionalVip(base_models.BASE):

    __data_model__ = data_models.AdditionalVip

    __tablename__ = "additional_vip"

    __table_args__ = (
        sa.PrimaryKeyConstraint('load_balancer_id', 'subnet_id',
                                name='pk_add_vip_load_balancer_subnet'),
    )

    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("load_balancer.id",
                      name="fk_add_vip_load_balancer_id"),
        nullable=False, index=True)
    ip_address = sa.Column(sa.String(64), nullable=True)
    port_id = sa.Column(sa.String(36), nullable=True)
    subnet_id = sa.Column(sa.String(36), nullable=True)
    network_id = sa.Column(sa.String(36), nullable=True)


class Listener(base_models.BASE, base_models.IdMixin,
               base_models.ProjectMixin, models.TimestampMixin,
               base_models.NameMixin, base_models.TagMixin):

    __data_model__ = data_models.Listener

    __tablename__ = "listener"

    __v2_wsme__ = listener.ListenerResponse

    __table_args__ = (
        sa.UniqueConstraint(
            'load_balancer_id', 'protocol', 'protocol_port',
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
    tls_certificate_id = sa.Column(sa.String(255), nullable=True)
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
                                     back_populates="listeners")
    default_pool = orm.relationship("Pool", uselist=False,
                                    back_populates="_default_listeners",
                                    cascade_backrefs=False)
    sni_containers = orm.relationship(
        'SNI', cascade='all,delete-orphan',
        uselist=True, backref=orm.backref('listener', uselist=False))

    l7policies = orm.relationship(
        'L7Policy', uselist=True, order_by='L7Policy.position',
        collection_class=orderinglist.ordering_list('position', count_from=1),
        cascade='delete', back_populates='listener')

    peer_port = sa.Column(sa.Integer(), nullable=True)
    insert_headers = sa.Column(sa.PickleType())
    timeout_client_data = sa.Column(sa.Integer, nullable=True)
    timeout_member_connect = sa.Column(sa.Integer, nullable=True)
    timeout_member_data = sa.Column(sa.Integer, nullable=True)
    timeout_tcp_inspect = sa.Column(sa.Integer, nullable=True)
    client_ca_tls_certificate_id = sa.Column(sa.String(255), nullable=True)
    client_authentication = sa.Column(
        sa.String(10),
        sa.ForeignKey("client_authentication_mode.name",
                      name="fk_listener_client_authentication_mode_name"),
        nullable=False, default=constants.CLIENT_AUTH_NONE)
    client_crl_container_id = sa.Column(sa.String(255), nullable=True)
    tls_ciphers = sa.Column(sa.String(2048), nullable=True)
    tls_versions = sa.Column(ScalarListType(), nullable=True)
    alpn_protocols = sa.Column(ScalarListType(), nullable=True)
    hsts_max_age = sa.Column(sa.Integer, nullable=True)
    hsts_include_subdomains = sa.Column(sa.Boolean, nullable=True)
    hsts_preload = sa.Column(sa.Boolean, nullable=True)

    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==Listener.id)',
        overlaps='_tags'
    )

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

    allowed_cidrs = orm.relationship(
        'ListenerCidr', cascade='all,delete-orphan',
        uselist=True, backref=orm.backref('listener', uselist=False))

    def __str__(self):
        return (f"Listener(id={self.id!r}, "
                f"default_pool={self.default_pool!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, protocol={self.protocol!r}, "
                f"protocol_port={self.protocol_port!r}, "
                f"enabled={self.enabled!r})")


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


class Amphora(base_models.BASE, base_models.IdMixin, models.TimestampMixin):

    __data_model__ = data_models.Amphora

    __tablename__ = "amphora"

    __v2_wsme__ = amphora.AmphoraResponse

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
    cached_zone = sa.Column(sa.String(255), nullable=True)
    image_id = sa.Column(sa.String(36), nullable=True)
    load_balancer = orm.relationship("LoadBalancer", uselist=False,
                                     back_populates='amphorae')
    compute_flavor = sa.Column(sa.String(255), nullable=True)

    def __str__(self):
        return (f"Amphora(id={self.id!r}, load_balancer_id="
                f"{self.load_balancer_id!r}, status={self.status!r}, "
                f"role={self.role!r}, lb_network_ip={self.lb_network_ip!r}, "
                f"vrrp_ip={self.vrrp_ip!r})")


class AmphoraHealth(base_models.BASE):
    __data_model__ = data_models.AmphoraHealth
    __tablename__ = "amphora_health"

    amphora_id = sa.Column(
        sa.String(36), nullable=False, primary_key=True)
    last_update = sa.Column(sa.DateTime, default=func.now(),
                            nullable=False)

    busy = sa.Column(sa.Boolean(), default=False, nullable=False)


class L7Rule(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
             models.TimestampMixin, base_models.TagMixin):

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
                                back_populates="l7rules")
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
    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==L7Rule.id)',
        overlaps='_tags'
    )

    def __str__(self):
        return (f"L7Rule(id={self.id!r}, project_id={self.project_id!r}, "
                f"provisioning_status={self.provisioning_status!r}, "
                f"type={self.type!r}, key={self.key!r}, value={self.value!r}, "
                f"invert={self.invert!r}, enabled={self.enabled!r})")


class L7Policy(base_models.BASE, base_models.IdMixin, base_models.ProjectMixin,
               models.TimestampMixin, base_models.NameMixin,
               base_models.TagMixin):

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
    redirect_prefix = sa.Column(
        sa.String(255),
        nullable=True)
    redirect_http_code = sa.Column(sa.Integer, nullable=True)
    position = sa.Column(sa.Integer, nullable=False)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    listener = orm.relationship("Listener", uselist=False,
                                back_populates="l7policies")
    redirect_pool = orm.relationship("Pool", uselist=False,
                                     back_populates="l7policies")
    l7rules = orm.relationship("L7Rule", uselist=True, cascade="delete",
                               back_populates="l7policy")
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
    _tags = orm.relationship(
        'Tags',
        single_parent=True,
        lazy='subquery',
        cascade='all,delete-orphan',
        primaryjoin='and_(foreign(Tags.resource_id)==L7Policy.id)',
        overlaps='_tags'
    )

    def __str__(self):
        return (f"L7Policy(id={self.id!r}, name={self.name!r}, "
                f"project_id={self.project_id!r}, "
                f"provisioning_status={self.provisioning_status!r}, "
                f"action={self.action!r}, position={self.position!r}, "
                f"enabled={self.enabled!r})")


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
    l7policy = sa.Column(sa.Integer(), nullable=True)
    l7rule = sa.Column(sa.Integer(), nullable=True)
    in_use_health_monitor = sa.Column(sa.Integer(), nullable=True)
    in_use_listener = sa.Column(sa.Integer(), nullable=True)
    in_use_load_balancer = sa.Column(sa.Integer(), nullable=True)
    in_use_member = sa.Column(sa.Integer(), nullable=True)
    in_use_pool = sa.Column(sa.Integer(), nullable=True)
    in_use_l7policy = sa.Column(sa.Integer(), nullable=True)
    in_use_l7rule = sa.Column(sa.Integer(), nullable=True)

    def __str__(self):
        return (f"Quotas(project_id={self.project_id!r}, "
                f"load_balancer={self.load_balancer!r}, "
                f"listener={self.listener!r}, pool={self.pool!r}, "
                f"health_monitor={self.health_monitor!r}, "
                f"member={self.member!r}, l7policy={self.l7policy!r}, "
                f"l7rule={self.l7rule!r})")


class FlavorProfile(base_models.BASE, base_models.IdMixin,
                    base_models.NameMixin):

    __data_model__ = data_models.FlavorProfile

    __tablename__ = "flavor_profile"

    __v2_wsme__ = flavor_profile.FlavorProfileResponse

    provider_name = sa.Column(sa.String(255), nullable=False)
    flavor_data = sa.Column(sa.String(4096), nullable=False)


class Flavor(base_models.BASE,
             base_models.IdMixin,
             base_models.NameMixin):

    __data_model__ = data_models.Flavor

    __tablename__ = "flavor"

    __v2_wsme__ = flavors.FlavorResponse

    __table_args__ = (
        sa.UniqueConstraint('name',
                            name='uq_flavor_name'),
    )

    description = sa.Column(sa.String(255), nullable=True)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    flavor_profile_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("flavor_profile.id",
                      name="fk_flavor_flavor_profile_id"),
        nullable=False)
    flavor_profile: Mapped["FlavorProfile"] = orm.relationship("FlavorProfile")


class AvailabilityZoneProfile(base_models.BASE, base_models.IdMixin,
                              base_models.NameMixin):

    __data_model__ = data_models.AvailabilityZoneProfile

    __tablename__ = "availability_zone_profile"

    __v2_wsme__ = availability_zone_profile.AvailabilityZoneProfileResponse

    provider_name = sa.Column(sa.String(255), nullable=False)
    availability_zone_data = sa.Column(sa.String(4096), nullable=False)


class AvailabilityZone(base_models.BASE,
                       base_models.NameMixin):

    __data_model__ = data_models.AvailabilityZone

    __tablename__ = "availability_zone"

    __v2_wsme__ = availability_zones.AvailabilityZoneResponse

    __table_args__ = (
        sa.PrimaryKeyConstraint('name'),
    )

    description = sa.Column(sa.String(255), nullable=True)
    enabled = sa.Column(sa.Boolean(), nullable=False)
    availability_zone_profile_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("availability_zone_profile.id",
                      name="fk_az_az_profile_id"),
        nullable=False)
    availability_zone_profile: Mapped["AvailabilityZoneProfile"] = (
        orm.relationship("AvailabilityZoneProfile"))


class ClientAuthenticationMode(base_models.BASE):

    __tablename__ = "client_authentication_mode"

    name = sa.Column(sa.String(10), primary_key=True, nullable=False)


class ListenerCidr(base_models.BASE):

    __data_model__ = data_models.ListenerCidr

    __tablename__ = "listener_cidr"
    __table_args__ = (
        sa.PrimaryKeyConstraint('listener_id', 'cidr'),
    )

    listener_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("listener.id", name="fk_listener_cidr_listener_id"),
        nullable=False)
    cidr = sa.Column(sa.String(64), nullable=False)


class VipSecurityGroup(base_models.BASE):

    __data_model__ = data_models.VipSecurityGroup

    __tablename__ = "vip_security_group"
    __table_args__ = (
        sa.PrimaryKeyConstraint('load_balancer_id', 'sg_id'),
    )

    load_balancer_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("vip.load_balancer_id", name="fk_vip_sg_vip_lb_id"),
        nullable=False)
    sg_id = sa.Column(sa.String(64), nullable=False)


class AmphoraMemberPort(base_models.BASE, models.TimestampMixin):

    __data_model__ = data_models.AmphoraMemberPort

    __tablename__ = "amphora_member_port"

    port_id = sa.Column(
        sa.String(36),
        primary_key=True)
    amphora_id = sa.Column(
        sa.String(36),
        sa.ForeignKey("amphora.id", name="fk_member_port_amphora_id"),
        nullable=False)
    network_id = sa.Column(
        sa.String(36))
