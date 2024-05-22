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

"""Add member vnic_type

Revision ID: 8db7a6443785
Revises: 3097e55493ae
Create Date: 2024-03-29 20:34:37.263847

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = '8db7a6443785'
down_revision = '3097e55493ae'


def upgrade():
    op.add_column(
        u'member',
        sa.Column(u'vnic_type', sa.String(64), nullable=False,
                  server_default=constants.VNIC_TYPE_NORMAL)
    )
