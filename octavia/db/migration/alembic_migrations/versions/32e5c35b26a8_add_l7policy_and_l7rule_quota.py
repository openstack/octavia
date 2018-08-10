# Copyright (c) 2018 China Telecom Corporation
# All Rights Reserved.
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

"""add l7policy and l7rule quota

Revision ID: 32e5c35b26a8
Revises: d3c8a090f3de
Create Date: 2018-08-10 09:13:59.383272

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '32e5c35b26a8'
down_revision = 'd3c8a090f3de'


def upgrade():
    op.add_column(u'quotas',
                  sa.Column('l7policy', sa.Integer(), nullable=True))
    op.add_column(u'quotas',
                  sa.Column('l7rule', sa.Integer(), nullable=True))
    op.add_column(u'quotas',
                  sa.Column('in_use_l7policy', sa.Integer(), nullable=True))
    op.add_column(u'quotas',
                  sa.Column('in_use_l7rule', sa.Integer(), nullable=True))
