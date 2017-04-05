# Copyright 2017 Huawei
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
#

"""Add QoS Policy ID column to VIP table

Revision ID: 0aee2b450512
Revises: bf171d0d91c3
Create Date: 2017-02-07 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0aee2b450512'
down_revision = 'bf171d0d91c3'


def upgrade():
    op.add_column('vip',
                  sa.Column('qos_policy_id',
                            sa.String(length=36),
                            nullable=True, server_default=None))
