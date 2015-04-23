#    Copyright 2015 Rackspace
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

"""Add vrrp_ip and ha_ip to amphora

Revision ID: 3e5b37a0bdb9
Revises: 92fe9857279
Create Date: 2015-03-24 18:17:36.998604

"""

# revision identifiers, used by Alembic.
revision = '3e5b37a0bdb9'
down_revision = '92fe9857279'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'amphora',
                  sa.Column(u'vrrp_ip', sa.String(64), nullable=True))
    op.add_column(u'amphora',
                  sa.Column(u'ha_ip', sa.String(64), nullable=True))


def downgrade():
    op.drop_column(u'amphora', u'vrrp_ip')
    op.drop_column(u'amphora', u'ha_ip')
