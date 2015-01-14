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

"""add lb_network_ip to amphora

Revision ID: 256852d5ff7c
Revises: 14892634e228
Create Date: 2015-01-13 16:18:57.359290

"""

# revision identifiers, used by Alembic.
revision = '256852d5ff7c'
down_revision = '14892634e228'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column(u'amphora', sa.Column(u'lb_network_ip', sa.String(64),
                                        nullable=True))


def downgrade():
    op.drop_column(u'amphora', u'lb_network_ip')
