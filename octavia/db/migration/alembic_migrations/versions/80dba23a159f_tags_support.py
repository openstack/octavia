#    Copyright 2018 Huawei
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
"""tags_support

Revision ID: 80dba23a159f
Revises: 55874a4ceed6
Create Date: 2018-10-15 15:29:27.258640

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '80dba23a159f'
down_revision = '55874a4ceed6'


def upgrade():
    op.create_table(
        u'tags',
        sa.Column(u'resource_id', sa.String(36), primary_key=True,
                  nullable=False),
        sa.Column(u'tag', sa.String(255), primary_key=True, nullable=False,
                  index=True),
    )
