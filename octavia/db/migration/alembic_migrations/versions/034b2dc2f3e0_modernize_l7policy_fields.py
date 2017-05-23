#    Copyright 2017 GoDaddy
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

"""modernize_l7policy_fields

Revision ID: 034b2dc2f3e0
Revises: fac584114642
Create Date: 2017-04-01 05:44:43.400535

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = '034b2dc2f3e0'
down_revision = 'fac584114642'


def upgrade():
    # Add timing data
    op.add_column(
        u'l7policy',
        sa.Column(u'created_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        u'l7policy',
        sa.Column(u'updated_at', sa.DateTime(), nullable=True)
    )

    # Add project_id
    op.add_column(
        u'l7policy',
        sa.Column(u'project_id', sa.String(36), nullable=True)
    )

    # Add new operating_status column, setting existing rows to ONLINE
    op.add_column(
        u'l7policy',
        sa.Column(u'operating_status', sa.String(16),
                  nullable=False, server_default=constants.ONLINE)
    )
    # Remove the default, as we don't actually want one
    op.alter_column(u'l7policy', u'operating_status',
                    existing_type=sa.String(16), server_default=None)
    # Add the foreign key for operating_status_name
    op.create_foreign_key(
        u'fk_l7policy_operating_status_name', u'l7policy',
        u'operating_status', [u'operating_status'], [u'name']
    )

    op.drop_constraint('fk_health_monitor_provisioning_status_name',
                       'health_monitor',
                       type_='foreignkey')

    op.drop_constraint('fk_l7policy_provisioning_status_name',
                       'l7policy',
                       type_='foreignkey')

    op.drop_constraint('fk_l7rule_provisioning_status_name',
                       'l7rule',
                       type_='foreignkey')

    op.drop_constraint('fk_member_provisioning_status_name',
                       'member',
                       type_='foreignkey')

    op.drop_constraint('fk_pool_provisioning_status_name',
                       'pool',
                       type_='foreignkey')

    # provisioning_status was mistakenly added as nullable, the fix is similar
    op.alter_column(u'l7policy', u'provisioning_status', nullable=False,
                    existing_type=sa.String(16),
                    server_default=constants.ACTIVE)
    op.alter_column(u'l7policy', u'provisioning_status',
                    existing_type=sa.String(16), server_default=None)

    # Fix the rest of these that were also mistakenly set as nullable in:
    # 9b5473976d6d_add_provisioning_status_to_objects.py
    op.alter_column(u'health_monitor', u'provisioning_status', nullable=False,
                    existing_type=sa.String(16),
                    server_default=constants.ACTIVE)
    op.alter_column(u'health_monitor', u'provisioning_status',
                    existing_type=sa.String(16), server_default=None)

    op.alter_column(u'member', u'provisioning_status', nullable=False,
                    existing_type=sa.String(16),
                    server_default=constants.ACTIVE)
    op.alter_column(u'member', u'provisioning_status',
                    existing_type=sa.String(16), server_default=None)

    op.alter_column(u'pool', u'provisioning_status', nullable=False,
                    existing_type=sa.String(16),
                    server_default=constants.ACTIVE)
    op.alter_column(u'pool', u'provisioning_status',
                    existing_type=sa.String(16), server_default=None)

    op.alter_column(u'l7rule', u'provisioning_status', nullable=False,
                    existing_type=sa.String(16),
                    server_default=constants.ACTIVE)
    op.alter_column(u'l7rule', u'provisioning_status',
                    existing_type=sa.String(16), server_default=None)

    op.create_foreign_key(
        u'fk_health_monitor_provisioning_status_name', u'health_monitor',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.create_foreign_key(
        u'fk_l7policy_provisioning_status_name', u'l7policy',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.create_foreign_key(
        u'fk_l7rule_provisioning_status_name', u'l7rule',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.create_foreign_key(
        u'fk_member_provisioning_status_name', u'member',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )

    op.create_foreign_key(
        u'fk_pool_provisioning_status_name', u'pool',
        u'provisioning_status', [u'provisioning_status'], [u'name']
    )
