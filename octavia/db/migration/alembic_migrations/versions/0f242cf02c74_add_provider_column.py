# Copyright 2018 Rackspace, US Inc.
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

"""Add provider column

Revision ID: 0f242cf02c74
Revises: 0fd2c131923f
Create Date: 2018-04-23 16:22:26.971048

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0f242cf02c74'
down_revision = '0fd2c131923f'


def upgrade():
    op.add_column(
        u'load_balancer',
        sa.Column(u'provider', sa.String(64), nullable=True)
    )
    op.execute("UPDATE load_balancer set provider='amphora' where provider "
               "is null")
