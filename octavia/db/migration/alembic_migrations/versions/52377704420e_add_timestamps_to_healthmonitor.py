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

"""add timestamps and operating_status to healthmonitor

Revision ID: 52377704420e
Revises: d85ca7258d21
Create Date: 2017-04-13 08:58:18.078170

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = '52377704420e'
down_revision = 'd85ca7258d21'


def upgrade():
    op.add_column(
        u'health_monitor',
        sa.Column(u'created_at', sa.DateTime(), nullable=True)
    )
    op.add_column(
        u'health_monitor',
        sa.Column(u'updated_at', sa.DateTime(), nullable=True)
    )

    op.add_column(u'health_monitor',
                  sa.Column(u'operating_status',
                            sa.String(16),
                            nullable=False,
                            server_default=constants.ONLINE)
                  )
    op.alter_column(u'health_monitor', u'operating_status',
                    existing_type=sa.String(16), server_default=None)

    op.create_foreign_key(
        u'fk_health_monitor_operating_status_name', u'health_monitor',
        u'operating_status', [u'operating_status'], [u'name']
    )
