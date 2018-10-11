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

"""Add Client Auth options

Revision ID: f21ae3f21adc
Revises: 2ad093f6353f
Create Date: 2018-10-01 20:47:52.405865

"""


from alembic import op
import sqlalchemy as sa

from octavia.common import constants

# revision identifiers, used by Alembic.
revision = 'f21ae3f21adc'
down_revision = '2ad093f6353f'


def upgrade():
    op.create_table(
        u'client_authentication_mode',
        sa.Column(u'name', sa.String(10), primary_key=True),
    )

    # Create temporary table for table data seeding
    insert_table = sa.table(
        u'client_authentication_mode',
        sa.column(u'name', sa.String),
    )

    op.bulk_insert(
        insert_table,
        [
            {'name': constants.CLIENT_AUTH_NONE},
            {'name': constants.CLIENT_AUTH_OPTIONAL},
            {'name': constants.CLIENT_AUTH_MANDATORY}
        ]
    )

    op.add_column(
        u'listener',
        sa.Column(u'client_authentication', sa.String(10),
                  sa.ForeignKey('client_authentication_mode.name'),
                  server_default=constants.CLIENT_AUTH_NONE, nullable=False)
    )
