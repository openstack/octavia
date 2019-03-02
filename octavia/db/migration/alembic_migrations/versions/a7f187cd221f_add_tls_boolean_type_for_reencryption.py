# Copyright 2018 Huawei
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

"""Add tls boolean type for backend re-encryption

Revision ID: a7f187cd221f
Revises: 74aae261694c
Create Date: 2018-11-01 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a7f187cd221f'
down_revision = '74aae261694c'


def upgrade():
    op.add_column(u'pool',
                  sa.Column(u'tls_enabled', sa.Boolean(),
                            server_default=sa.sql.expression.false(),
                            nullable=False))
