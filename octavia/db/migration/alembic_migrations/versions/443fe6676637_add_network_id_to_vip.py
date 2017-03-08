# Copyright 2017 GoDaddy
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
"""Add a column network_id in table vip

Revision ID: 443fe6676637
Revises: 3f8ff3be828e
Create Date: 2017-02-06 15:21:25.637744

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '443fe6676637'
down_revision = '3f8ff3be828e'


def upgrade():
    op.add_column(u'vip',
                  sa.Column(u'network_id', sa.String(36), nullable=True))
