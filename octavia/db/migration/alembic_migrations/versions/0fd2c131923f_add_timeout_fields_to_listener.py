# Copyright 2018 GoDaddy
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

"""add timeout fields to listener

Revision ID: 0fd2c131923f
Revises: ba35e0fb88e1
Create Date: 2018-03-23 03:34:26.657254

"""

from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = '0fd2c131923f'
down_revision = 'ba35e0fb88e1'


def upgrade():
    op.add_column('listener',
                  sa.Column('timeout_client_data',
                            sa.Integer(), nullable=True,
                            default=constants.DEFAULT_TIMEOUT_CLIENT_DATA))
    op.add_column('listener',
                  sa.Column('timeout_member_connect',
                            sa.Integer(), nullable=True,
                            default=constants.DEFAULT_TIMEOUT_MEMBER_CONNECT))
    op.add_column('listener',
                  sa.Column('timeout_member_data',
                            sa.Integer(), nullable=True,
                            default=constants.DEFAULT_TIMEOUT_MEMBER_DATA))
    op.add_column('listener',
                  sa.Column('timeout_tcp_inspect',
                            sa.Integer(), nullable=True,
                            default=constants.DEFAULT_TIMEOUT_TCP_INSPECT))
