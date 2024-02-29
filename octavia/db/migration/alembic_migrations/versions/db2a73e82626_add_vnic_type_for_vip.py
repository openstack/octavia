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

"""Add vnic_type for VIP

Revision ID: db2a73e82626
Revises: 632152d2d32e
Create Date: 2023-11-09 21:57:05.302435

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = 'db2a73e82626'
down_revision = '632152d2d32e'


def upgrade():
    op.add_column(
        u'vip',
        sa.Column(u'vnic_type', sa.String(64), nullable=False,
                  server_default=constants.VNIC_TYPE_NORMAL)
    )
