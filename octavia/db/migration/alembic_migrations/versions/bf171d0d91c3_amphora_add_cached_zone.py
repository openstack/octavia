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

"""add cached_zone to amphora

Revision ID: bf171d0d91c3
Revises: 4aeb9e23ad43
Create Date: 2017-10-06 12:07:34.290451

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'bf171d0d91c3'
down_revision = '4aeb9e23ad43'


def upgrade():
    op.add_column(u'amphora', sa.Column(u'cached_zone', sa.String(255),
                                        nullable=True))
