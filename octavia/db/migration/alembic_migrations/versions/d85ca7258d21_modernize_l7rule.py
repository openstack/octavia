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

"""modernize l7rule

Revision ID: d85ca7258d21
Revises: 034b2dc2f3e0
Create Date: 2017-04-04 06:26:55.287198

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = 'd85ca7258d21'
down_revision = '034b2dc2f3e0'


def upgrade():
    # Add timing data
    op.add_column(
        u'l7rule',
        sa.Column(u'created_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        u'l7rule',
        sa.Column(u'updated_at', sa.DateTime(), nullable=True)
    )

    # Add project_id
    op.add_column(
        u'l7rule',
        sa.Column(u'project_id', sa.String(36), nullable=True)
    )

    # Add enabled
    op.add_column(
        u'l7rule',
        sa.Column(u'enabled', sa.Boolean(), nullable=False)
    )

    # Add new operating_status column, setting existing rows to ONLINE
    op.add_column(
        u'l7rule',
        sa.Column(u'operating_status', sa.String(16),
                  nullable=False, server_default=constants.ONLINE)
    )
    # Remove the default, as we don't actually want one
    op.alter_column(u'l7rule', u'operating_status',
                    existing_type=sa.String(16), server_default=None)
    # Add the foreign key for operating_status_name
    op.create_foreign_key(
        u'fk_l7rule_operating_status_name', u'l7rule',
        u'operating_status', [u'operating_status'], [u'name']
    )
