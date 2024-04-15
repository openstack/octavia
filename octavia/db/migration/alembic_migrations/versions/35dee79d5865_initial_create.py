#    Copyright 2014 Rackspace
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

'''initial_create

Revision ID: 35dee79d5865
Revises: None
Create Date: 2014-08-15 11:01:14.897223

'''

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

# revision identifiers, used by Alembic.
revision = '35dee79d5865'
down_revision = None


def upgrade():
    # Create lookup tables
    op.create_table(
        'health_monitor_type',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    # Create temporary table for table data seeding
    insert_table = sql.table(
        'health_monitor_type',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'HTTP'},
            {'name': 'HTTPS'},
            {'name': 'TCP'}
        ]
    )

    op.create_table(
        'protocol',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'protocol',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'HTTP'},
            {'name': 'HTTPS'},
            {'name': 'TCP'}
        ]
    )

    op.create_table(
        'algorithm',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'algorithm',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'ROUND_ROBIN'},
            {'name': 'LEAST_CONNECTIONS'},
            {'name': 'SOURCE_IP'}
        ]
    )

    op.create_table(
        'session_persistence_type',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'session_persistence_type',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'SOURCE_IP'},
            {'name': 'HTTP_COOKIE'},
            {'name': 'APP_COOKIE'}
        ]
    )

    op.create_table(
        'provisioning_status',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'provisioning_status',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'ACTIVE'},
            {'name': 'PENDING_CREATE'},
            {'name': 'PENDING_UPDATE'},
            {'name': 'PENDING_DELETE'},
            {'name': 'DELETED'},
            {'name': 'ERROR'}
        ]
    )

    op.create_table(
        'operating_status',
        sa.Column('name', sa.String(30), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True)
    )

    insert_table = sql.table(
        'operating_status',
        sql.column('name', sa.String),
        sql.column('description', sa.String)
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': 'ONLINE'},
            {'name': 'OFFLINE'},
            {'name': 'DEGRADED'},
            {'name': 'ERROR'}
        ]
    )

    op.create_table(
        'pool',
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('protocol', sa.String(16), nullable=False),
        sa.Column('lb_algorithm', sa.String(16), nullable=False),
        sa.Column('operating_status', sa.String(16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['protocol'],
                                ['protocol.name'],
                                name='fk_pool_protocol_name'),
        sa.ForeignKeyConstraint(['lb_algorithm'],
                                ['algorithm.name'],
                                name='fk_pool_algorithm_name'),
        sa.ForeignKeyConstraint(['operating_status'],
                                ['operating_status.name'],
                                name='fk_pool_operating_status_name')
    )

    op.create_table(
        'health_monitor',
        sa.Column('pool_id', sa.String(36), nullable=False),
        sa.Column('type', sa.String(36), nullable=False),
        sa.Column('delay', sa.Integer(), nullable=False),
        sa.Column('timeout', sa.Integer(), nullable=False),
        sa.Column('fall_threshold', sa.Integer(), nullable=False),
        sa.Column('rise_threshold', sa.Integer(), nullable=False),
        sa.Column('http_method', sa.String(16), nullable=True),
        sa.Column('url_path', sa.String(255), nullable=True),
        sa.Column('expected_codes', sa.String(64), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('pool_id'),
        sa.ForeignKeyConstraint(['pool_id'], ['pool.id'],
                                name='fk_health_monitor_pool_id'),
        sa.ForeignKeyConstraint(
            ['type'], ['health_monitor_type.name'],
            name='fk_health_monitor_health_monitor_type_name')
    )

    op.create_table(
        'session_persistence',
        sa.Column('pool_id', sa.String(36), nullable=False),
        sa.Column('type', sa.String(16), nullable=False),
        sa.Column('cookie_name', sa.String(255), nullable=True),
        sa.ForeignKeyConstraint(
            ['type'], ['session_persistence_type.name'],
            name='fk_session_persistence_session_persistence_type_name'),
        sa.ForeignKeyConstraint(['pool_id'], ['pool.id'],
                                name='fk_session_persistence_pool_id'),
        sa.PrimaryKeyConstraint('pool_id')
    )

    op.create_table(
        'member',
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('pool_id', sa.String(36), nullable=False),
        sa.Column('subnet_id', sa.String(36), nullable=True),
        sa.Column('address', sa.String(64), nullable=False),
        sa.Column('protocol_port', sa.Integer(), nullable=False),
        sa.Column('weight', sa.Integer(), nullable=True),
        sa.Column('operating_status', sa.String(16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['pool_id'], ['pool.id'],
                                name='fk_member_pool_id'),
        sa.ForeignKeyConstraint(['operating_status'],
                                ['operating_status.name'],
                                name='fk_member_operating_status_name'),
        sa.UniqueConstraint('pool_id', 'address', 'protocol_port',
                            name='uq_member_pool_id_address_protocol_port')
    )

    op.create_table(
        'load_balancer',
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('provisioning_status', sa.String(16), nullable=False),
        sa.Column('operating_status', sa.String(16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['provisioning_status'], ['provisioning_status.name'],
            name='fk_load_balancer_provisioning_status_name'),
        sa.ForeignKeyConstraint(['operating_status'],
                                ['operating_status.name'],
                                name='fk_load_balancer_operating_status_name')
    )

    op.create_table(
        'vip',
        sa.Column('load_balancer_id', sa.String(36), nullable=False),
        sa.Column('ip_address', sa.String(36), nullable=True),
        sa.Column('net_port_id', sa.String(36), nullable=True),
        sa.Column('subnet_id', sa.String(36), nullable=True),
        sa.Column('floating_ip_id', sa.String(36), nullable=True),
        sa.Column('floating_ip_network_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('load_balancer_id'),
        sa.ForeignKeyConstraint(['load_balancer_id'], ['load_balancer.id'],
                                name='fk_vip_load_balancer_id')
    )

    op.create_table(
        'listener',
        sa.Column('tenant_id', sa.String(255), nullable=True),
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(255), nullable=True),
        sa.Column('description', sa.String(255), nullable=True),
        sa.Column('protocol', sa.String(16), nullable=False),
        sa.Column('protocol_port', sa.Integer(), nullable=False),
        sa.Column('connection_limit', sa.Integer(), nullable=True),
        sa.Column('load_balancer_id', sa.String(36), nullable=True),
        sa.Column('tls_certificate_id', sa.String(36), nullable=True),
        sa.Column('default_pool_id', sa.String(36), nullable=True),
        sa.Column('provisioning_status', sa.String(16), nullable=False),
        sa.Column('operating_status', sa.String(16), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['load_balancer_id'], ['load_balancer.id'],
                                name='fk_listener_load_balancer_id'),
        sa.ForeignKeyConstraint(['default_pool_id'], ['pool.id'],
                                name='fk_listener_pool_id'),
        sa.ForeignKeyConstraint(['protocol'], ['protocol.name'],
                                name='fk_listener_protocol_name'),
        sa.ForeignKeyConstraint(['provisioning_status'],
                                ['provisioning_status.name'],
                                name='fk_listener_provisioning_status_name'),
        sa.ForeignKeyConstraint(['operating_status'],
                                ['operating_status.name'],
                                name='fk_listener_operating_status_name'),
        sa.UniqueConstraint('default_pool_id',
                            name='uq_listener_default_pool_id'),
        sa.UniqueConstraint(
            'load_balancer_id', 'protocol_port',
            name='uq_listener_load_balancer_id_protocol_port'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table(
        'sni',
        sa.Column('listener_id', sa.String(36), nullable=False),
        sa.Column('tls_container_id', sa.String(36), nullable=False),
        sa.Column('position', sa.Integer, nullable=True),
        sa.ForeignKeyConstraint(['listener_id'], ['listener.id'],
                                name='fk_sni_listener_id'),
        sa.PrimaryKeyConstraint('listener_id', 'tls_container_id')
    )

    op.create_table(
        'listener_statistics',
        sa.Column('listener_id', sa.String(36), nullable=False),
        sa.Column('bytes_in', sa.BigInteger(), nullable=False),
        sa.Column('bytes_out', sa.BigInteger(), nullable=False),
        sa.Column('active_connections', sa.Integer(), nullable=False),
        sa.Column('total_connections', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('listener_id'),
        sa.ForeignKeyConstraint(['listener_id'], ['listener.id'],
                                name='fk_listener_statistics_listener_id')
    )

    op.create_table(
        'amphora',
        # id should come from the service providing the amphora (i.e. nova)
        sa.Column('id', sa.String(36), nullable=False, autoincrement=False),
        sa.Column('host_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(36), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['status'], ['provisioning_status.name'],
            name='fk_container_provisioning_status_name')
    )

    op.create_table(
        'load_balancer_amphora',
        sa.Column('amphora_id', sa.String(36), nullable=False),
        sa.Column('load_balancer_id', sa.String(36), nullable=False),
        sa.ForeignKeyConstraint(
            ['load_balancer_id'], ['load_balancer.id'],
            name='fk_load_balancer_amphora_load_balancer_id'),
        sa.ForeignKeyConstraint(['amphora_id'],
                                ['amphora.id'],
                                name='fk_load_balancer_amphora_id'),
        sa.PrimaryKeyConstraint('amphora_id', 'load_balancer_id')
    )
