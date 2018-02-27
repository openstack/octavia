#    Copyright 2017 GoDaddy
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

"""amphora add image id

Revision ID: 034756a182a2
Revises: 10d38216ad34
Create Date: 2018-02-26 17:38:37.971677

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '034756a182a2'
down_revision = '10d38216ad34'


def upgrade():
    op.add_column(
        u'amphora',
        sa.Column(u'image_id', sa.String(36), nullable=True)
    )
