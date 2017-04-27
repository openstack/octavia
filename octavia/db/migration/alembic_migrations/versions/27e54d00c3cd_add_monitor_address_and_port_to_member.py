# Copyright 2017 EayunStack, Inc.
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

"""add monitor address and port to member

Revision ID: 27e54d00c3cd
Revises: 5309960964f8
Create Date: 2017-05-01 23:12:16.695581

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '27e54d00c3cd'
down_revision = '5309960964f8'


def upgrade():
    op.add_column(u'member',
                  sa.Column(u'monitor_address',
                            sa.String(64),
                            nullable=True)
                  )
    op.add_column(u'member',
                  sa.Column(u'monitor_port',
                            sa.Integer(),
                            nullable=True)
                  )
