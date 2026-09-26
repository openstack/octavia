# Copyright 2018 OpenStack Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License.

"""Add the active-active distributor data model.

This is the modernized form of OpenDev's historical
``5bbd6742b ACTIVE-ACTIVE: Initial distributor data model`` patch.  The
original patch predates the current migration head, so its schema additions
are replayed here against the 2024.1 database lineage.
"""

from alembic import op
import sqlalchemy as sa


revision = 'd5cf3da30ed8'
down_revision = 'db2a73e82626'
branch_labels = None
depends_on = None


def upgrade():
    topology = sa.sql.table(
        'lb_topology', sa.sql.column('name', sa.String),
        sa.sql.column('description', sa.String))
    op.bulk_insert(topology, [
        {'name': 'ACTIVE_ACTIVE',
         'description': 'N+1 amphorae with a distributor'},
    ])

    roles = sa.sql.table(
        'amphora_roles', sa.sql.column('name', sa.String),
        sa.sql.column('description', sa.String))
    op.bulk_insert(roles, [
        {'name': 'IN_CLUSTER',
         'description': 'Active member of an amphora cluster'},
        {'name': 'IN_CLUSTER_STANDBY',
         'description': 'Standby member of an amphora cluster'},
    ])

    op.create_table(
        'distributor',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('distributor_driver', sa.String(64), nullable=False),
        sa.Column('compute_id', sa.String(36), nullable=True),
        sa.Column('lb_network_ip', sa.String(64), nullable=True),
        sa.Column('frontend_port_id', sa.String(36), nullable=True),
        sa.Column('frontend_mac', sa.String(32), nullable=True),
        sa.Column('topology', sa.String(36), nullable=True),
        sa.Column('provisioning_status', sa.String(16), nullable=False),
        sa.Column('operating_status', sa.String(16), nullable=False),
    )
    op.create_foreign_key(
        'fk_distributor_topology', 'distributor', 'lb_topology',
        ['topology'], ['name'])
    op.create_foreign_key(
        'fk_distributor_provisioning_status_name', 'distributor',
        'provisioning_status', ['provisioning_status'], ['name'])
    op.create_foreign_key(
        'fk_distributor_operating_status_name', 'distributor',
        'operating_status', ['operating_status'], ['name'])

    op.create_table(
        'amphora_service_type',
        sa.Column('name', sa.String(36), primary_key=True),
        sa.Column('description', sa.String(255), nullable=True))
    service_types = sa.sql.table(
        'amphora_service_type', sa.sql.column('name', sa.String),
        sa.sql.column('description', sa.String))
    op.bulk_insert(service_types, [
        {'name': 'LOADBALANCER'}, {'name': 'DISTRIBUTOR'}])

    op.add_column('amphora', sa.Column('distributor_id', sa.String(36)))
    op.create_foreign_key(
        'fk_amphora_distributor_id', 'amphora', 'distributor',
        ['distributor_id'], ['id'])
    op.add_column('amphora', sa.Column('service_type', sa.String(36)))
    op.create_foreign_key(
        'fk_amphora_service_type', 'amphora', 'amphora_service_type',
        ['service_type'], ['name'])
    op.execute("UPDATE amphora SET service_type = 'LOADBALANCER'")

    op.add_column('load_balancer', sa.Column('distributor_id', sa.String(36)))
    op.create_foreign_key(
        'fk_load_balancer_distributor_id', 'load_balancer', 'distributor',
        ['distributor_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_load_balancer_distributor_id', 'load_balancer',
                       type_='foreignkey')
    op.drop_column('load_balancer', 'distributor_id')
    op.drop_constraint('fk_amphora_service_type', 'amphora',
                       type_='foreignkey')
    op.drop_column('amphora', 'service_type')
    op.drop_constraint('fk_amphora_distributor_id', 'amphora',
                       type_='foreignkey')
    op.drop_column('amphora', 'distributor_id')
    op.drop_table('amphora_service_type')
    op.drop_table('distributor')
    op.execute("DELETE FROM amphora_roles WHERE name = 'IN_CLUSTER'")
    op.execute("DELETE FROM amphora_roles WHERE name = 'IN_CLUSTER_STANDBY'")
    op.execute("DELETE FROM lb_topology WHERE name = 'ACTIVE_ACTIVE'")
