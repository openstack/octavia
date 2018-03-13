# Copyright 2016 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

"""add backup field to member

Revision ID: ba35e0fb88e1
Revises: 034756a182a2
Create Date: 2018-03-14 00:46:16.281857

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'ba35e0fb88e1'
down_revision = '034756a182a2'


def upgrade():
    op.add_column(u'member', sa.Column(u'backup', sa.Boolean(),
                                       nullable=False, default=False))
