#    Copyright 2018 Rackspace, US Inc.
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
"""add_flavor_id_to_lb

Revision ID: 211982b05afc
Revises: b9c703669314
Create Date: 2018-11-30 14:57:28.559884

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '211982b05afc'
down_revision = 'b9c703669314'


def upgrade():
    op.add_column('load_balancer',
                  sa.Column('flavor_id', sa.String(36), nullable=True))
