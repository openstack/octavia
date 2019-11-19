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

"""Add lb flavor ID constraint

Revision ID: e37941b010db
Revises: dcf88e59aae4
Create Date: 2019-10-31 10:09:37.869653

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import sql

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = 'e37941b010db'
down_revision = 'dcf88e59aae4'


def upgrade():
    insert_table = sql.table(
        u'flavor_profile',
        sa.Column(u'id', sa.String(36), nullable=False),
        sa.Column(u'name', sa.String(255), nullable=False),
        sa.Column(u'provider_name', sa.String(255), nullable=False),
        sa.Column(u'flavor_data', sa.String(4096), nullable=False),
    )

    op.bulk_insert(
        insert_table,
        [
            {'id': constants.NIL_UUID, 'name': 'DELETED-PLACEHOLDER',
             'provider_name': 'DELETED', 'flavor_data': '{}'},
        ]
    )

    insert_table = sql.table(
        u'flavor',
        sa.Column(u'id', sa.String(36), nullable=False),
        sa.Column(u'name', sa.String(255), nullable=False),
        sa.Column(u'description', sa.String(255), nullable=True),
        sa.Column(u'enabled', sa.Boolean(), nullable=False),
        sa.Column(u'flavor_profile_id', sa.String(36), nullable=False),
    )

    op.bulk_insert(
        insert_table,
        [
            {'id': constants.NIL_UUID, 'name': 'DELETED-PLACEHOLDER',
             'description': 'Placeholder for DELETED LBs with DELETED flavors',
             'enabled': False, 'flavor_profile_id': constants.NIL_UUID}
        ]
    )

    # Make sure any existing load balancers with invalid flavor_id
    # map to a valid flavor.
    # Note: constant is not used here to not trigger security tool errors.
    op.execute("UPDATE load_balancer LEFT JOIN flavor ON "
               "load_balancer.flavor_id = flavor.id SET "
               "load_balancer.flavor_id = "
               "'00000000-0000-0000-0000-000000000000' WHERE "
               "flavor.id IS NULL and load_balancer.flavor_id IS NOT NULL")

    op.create_foreign_key('fk_loadbalancer_flavor_id', 'load_balancer',
                          'flavor', ['flavor_id'], ['id'])
