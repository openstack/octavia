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

"""add availability_zone table

Revision ID: c761c8a71579
Revises: e37941b010db
Create Date: 2019-11-11 18:53:15.428386

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = 'c761c8a71579'
down_revision = 'e37941b010db'


def upgrade():
    azp_table = op.create_table(
        u'availability_zone_profile',
        sa.Column(u'id', sa.String(36), nullable=False),
        sa.Column(u'name', sa.String(255), nullable=False),
        sa.Column(u'provider_name', sa.String(255), nullable=False),
        sa.Column(u'availability_zone_data', sa.String(4096), nullable=False),
        sa.PrimaryKeyConstraint(u'id'))

    op.bulk_insert(
        azp_table,
        [
            {'id': constants.NIL_UUID, 'name': 'DELETED-PLACEHOLDER',
             'provider_name': 'DELETED', 'availability_zone_data': '{}'},
        ]
    )

    az_table = op.create_table(
        u'availability_zone',
        sa.Column(u'name', sa.String(255), nullable=False),
        sa.Column(u'description', sa.String(255), nullable=True),
        sa.Column(u'enabled', sa.Boolean(), nullable=False),
        sa.Column(u'availability_zone_profile_id', sa.String(36),
                  nullable=False),
        sa.ForeignKeyConstraint([u'availability_zone_profile_id'],
                                [u'availability_zone_profile.id'],
                                name=u'fk_az_az_profile_id'),
        sa.PrimaryKeyConstraint(u'name'),)

    op.bulk_insert(
        az_table,
        [
            {'name': constants.NIL_UUID,
             'description': 'Placeholder for DELETED LBs with DELETED '
                            'availability zones',
             'enabled': False,
             'availability_zone_profile_id': constants.NIL_UUID}
        ]
    )
